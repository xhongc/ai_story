import json
import re
from json import JSONDecodeError

import requests
from django.conf import settings

from .local_agent import LocalAgentResponder


AGENT_UI_BLOCK_RE = re.compile(r'```agent-ui\s*(\{.*?\})\s*```', re.DOTALL)


class AgentGateway:
    def __init__(self):
        self.server_base_url = (getattr(settings, 'AGENT_SERVER_BASE_URL', '') or '').rstrip('/')
        self.server_username = (getattr(settings, 'AGENT_SERVER_USERNAME', '') or '').strip()
        self.server_password = (getattr(settings, 'AGENT_SERVER_PASSWORD', '') or '').strip()
        self.model_provider_id = (getattr(settings, 'AGENT_MODEL_PROVIDER_ID', '') or 'opencode').strip()
        self.model_id = (getattr(settings, 'AGENT_MODEL_ID', '') or 'big-pickle').strip()
        self.model_variant = (getattr(settings, 'AGENT_MODEL_VARIANT', '') or '').strip()
        self.agent_name = (getattr(settings, 'AGENT_REMOTE_AGENT_NAME', '') or '').strip()
        self.project_directory = str(getattr(settings, 'BASE_DIR').parent)
        self.local_responder = LocalAgentResponder()

    def _headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.server_username and self.server_password:
            session = requests.Session()
            session.auth = (self.server_username, self.server_password)
            headers.update(requests.utils.default_headers())
        return headers

    def _session(self):
        session = requests.Session()
        if self.server_username and self.server_password:
            session.auth = (self.server_username, self.server_password)
        session.headers.update(self._headers())
        return session

    def _query_params(self):
        return {'directory': self.project_directory}

    def _build_system_prompt(self, context, ui_context):
        return (
            '你是 AI Story 的页面助手。'
            '你可以结合业务上下文给出简洁建议。'
            '你不能假设自己直接操作浏览器。'
            '如果需要前端执行动作，请在回复末尾输出 fenced code block，标签必须是 agent-ui，JSON 结构为 {"ui_intents": [...]}。'
            'intent 只能从 allowed_ui_actions 中选择。'
            '正文保持简洁，先解释，再给 0-3 个动作。'
            f'\n\n业务上下文:\n{json.dumps(context, ensure_ascii=False)}'
            f'\n\nUI 上下文:\n{json.dumps(ui_context or {}, ensure_ascii=False)}'
        )

    def _build_message_parts(self, user_message):
        return [{
            'type': 'text',
            'text': user_message,
        }]

    def _build_prompt_payload(self, user_message, context, ui_context):
        payload = {
            'model': {
                'providerID': self.model_provider_id,
                'modelID': self.model_id,
            },
            'system': self._build_system_prompt(context, ui_context),
            'parts': self._build_message_parts(user_message),
            'noReply': False,
        }
        if self.model_variant:
            payload['variant'] = self.model_variant
        if self.agent_name:
            payload['agent'] = self.agent_name
        return payload

    def ensure_remote_session(self, *, session, manager=None, user_id=None, scope_key=None):
        remote_session_id = session.get('agent_session_id')
        if remote_session_id:
            return remote_session_id

        client = self._session()
        response = client.post(
            f'{self.server_base_url}/session',
            params=self._query_params(),
            json={'title': session.get('scope_key') or session.get('route_name') or 'ai-story-agent'},
            timeout=30,
        )
        response.raise_for_status()
        remote_session = response.json()
        remote_session_id = remote_session['id']

        if manager and user_id and scope_key:
            manager.update_session(user_id, scope_key, agent_session_id=remote_session_id)

        return remote_session_id

    def abort_session(self, remote_session_id):
        if not self.server_base_url or not remote_session_id:
            return False

        client = self._session()
        response = client.post(
            f'{self.server_base_url}/session/{remote_session_id}/abort',
            params=self._query_params(),
            timeout=15,
        )
        response.raise_for_status()
        return True

    def stream_response(self, *, session, user_message, context, ui_context=None, manager=None, user_id=None, scope_key=None):
        if not self.server_base_url:
            yield from self.local_responder.stream_events(
                user_message=user_message,
                context=context,
                ui_context=ui_context,
                history=session.get('messages') or [],
            )
            return

        remote_session_id = self.ensure_remote_session(
            session=session,
            manager=manager,
            user_id=user_id,
            scope_key=scope_key,
        )

        client = self._session()
        event_response = client.get(
            f'{self.server_base_url}/event',
            params=self._query_params(),
            stream=True,
            timeout=(10, 120),
        )
        event_response.raise_for_status()

        prompt_response = client.post(
            f'{self.server_base_url}/session/{remote_session_id}/prompt_async',
            params=self._query_params(),
            json=self._build_prompt_payload(user_message, context, ui_context),
            timeout=30,
        )
        prompt_response.raise_for_status()

        assistant_message_id = None
        accumulated_text = ''
        seen_connected = False

        try:
            for payload in self._iter_sse_events(event_response):
                event_type = payload.get('type')
                properties = payload.get('properties') or {}

                if not seen_connected:
                    seen_connected = True
                    yield {'type': 'connected'}

                if event_type == 'message.updated':
                    info = properties.get('info') or {}
                    if info.get('sessionID') != remote_session_id:
                        continue
                    if info.get('role') == 'assistant':
                        assistant_message_id = info.get('id') or assistant_message_id
                        error = info.get('error') or {}
                        if error:
                            error_message = self._extract_error_message(error)
                            yield {'type': 'error', 'message': error_message}
                            return

                elif event_type == 'message.part.delta':
                    if properties.get('sessionID') != remote_session_id:
                        continue
                    if assistant_message_id and properties.get('messageID') != assistant_message_id:
                        continue
                    if properties.get('field') != 'text':
                        continue
                    delta = properties.get('delta') or ''
                    accumulated_text += delta
                    if delta:
                        yield {'type': 'token', 'content': delta}

                elif event_type == 'message.part.updated':
                    part = properties.get('part') or {}
                    if part.get('sessionID') != remote_session_id:
                        continue
                    if assistant_message_id and part.get('messageID') != assistant_message_id:
                        continue
                    if part.get('type') == 'text' and part.get('text') and not accumulated_text:
                        accumulated_text = part.get('text') or ''

                elif event_type == 'session.error':
                    if properties.get('sessionID') != remote_session_id:
                        continue
                    yield {'type': 'error', 'message': self._extract_error_message(properties.get('error') or {})}
                    return

                elif event_type == 'session.idle':
                    if properties.get('sessionID') != remote_session_id:
                        continue
                    break
        finally:
            event_response.close()

        full_text = self.fetch_assistant_text(client, remote_session_id, assistant_message_id) or accumulated_text
        visible_text, ui_intents = self._extract_agent_ui(full_text)
        yield {
            'type': 'message',
            'role': 'assistant',
            'content': visible_text,
        }
        for intent in ui_intents:
            yield {
                'type': 'ui_intent',
                **intent,
            }
        yield {'type': 'done'}

    def _iter_sse_events(self, response):
        event_lines = []
        for raw_line in response.iter_lines(chunk_size=1, decode_unicode=True):
            if raw_line == '':
                payload = self._parse_sse_event_lines(event_lines)
                event_lines = []
                if payload is not None:
                    yield payload
                continue

            if raw_line is None:
                continue
            event_lines.append(raw_line)

        payload = self._parse_sse_event_lines(event_lines)
        if payload is not None:
            yield payload

    def _parse_sse_event_lines(self, lines):
        if not lines:
            return None

        data_lines = []
        for line in lines:
            if line.startswith('data: '):
                data_lines.append(line[6:])
            elif line.startswith('data:'):
                data_lines.append(line[5:])

        if not data_lines:
            return None

        payload_text = '\n'.join(data_lines)
        try:
            return json.loads(payload_text)
        except JSONDecodeError:
            return None

    def fetch_assistant_text(self, client, remote_session_id, assistant_message_id=None):
        response = client.get(
            f'{self.server_base_url}/session/{remote_session_id}/message',
            params={**self._query_params(), 'limit': 8},
            timeout=20,
        )
        response.raise_for_status()
        messages = response.json() or []

        target = None
        if assistant_message_id:
            for item in messages:
                info = item.get('info') or {}
                if info.get('id') == assistant_message_id:
                    target = item
                    break

        if not target:
            for item in reversed(messages):
                info = item.get('info') or {}
                if info.get('role') == 'assistant':
                    target = item
                    break

        if not target:
            return ''

        text_parts = []
        for part in target.get('parts') or []:
            if part.get('type') == 'text':
                text_parts.append(part.get('text') or '')

        return ''.join(text_parts).strip()

    def _extract_error_message(self, error):
        if not error:
            return 'Agent 服务处理失败'
        data = error.get('data') or {}
        return data.get('message') or error.get('message') or error.get('name') or 'Agent 服务处理失败'

    def _extract_agent_ui(self, text):
        content = (text or '').strip()
        ui_intents = []
        match = AGENT_UI_BLOCK_RE.search(content)
        if not match:
            return content, ui_intents

        raw_json = match.group(1)
        visible_text = AGENT_UI_BLOCK_RE.sub('', content).strip()
        try:
            payload = json.loads(raw_json)
            ui_intents = payload.get('ui_intents') or []
        except json.JSONDecodeError:
            return content, []

        normalized = []
        for index, item in enumerate(ui_intents):
            if not isinstance(item, dict):
                continue
            normalized.append({
                'action_id': item.get('action_id') or f'ui_{index + 1}',
                'intent': item.get('intent') or '',
                'label': item.get('label') or item.get('intent') or '执行动作',
                'description': item.get('description') or '',
                'params': item.get('params') or {},
                'requires_confirmation': bool(item.get('requires_confirmation', False)),
            })
        return visible_text, normalized[:3]
