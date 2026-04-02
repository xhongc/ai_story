import json
import re
from json import JSONDecodeError

import requests
from django.conf import settings

from apps.models.models import ModelProvider
from apps.models.opencode_config import OpencodeConfigSyncService
from .builtin_models import BuiltinAgentModelRegistry
from .local_agent import LocalAgentResponder


AGENT_UI_BLOCK_RE = re.compile(r'```agent-ui\s*(\{.*?\})\s*```', re.DOTALL)
RUNTIME_PROVIDER_MAP_UNSET = object()


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
            '除非用户明确要求，否则不要主动搜索代码、不要调用工具、不要进入长链路研究。'
            '优先直接根据 system prompt 中提供的业务上下文与 UI 上下文回答。'
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

    def _fetch_runtime_provider_map(self):
        if not self.server_base_url:
            return {}

        client = self._session()
        response = client.get(
            f'{self.server_base_url}/config/providers',
            params=self._query_params(),
            timeout=15,
        )
        response.raise_for_status()

        payload = response.json() or {}
        providers = payload.get('providers') or []
        return {
            item.get('id'): item
            for item in providers
            if item.get('id')
        }

    def fetch_runtime_provider_map_safe(self):
        if not self.server_base_url:
            return {}
        try:
            return self._fetch_runtime_provider_map()
        except requests.RequestException:
            return None

    def _runtime_provider_has_model(self, provider_info, model_id):
        models = provider_info.get('models') or {}
        if isinstance(models, dict):
            return model_id in models
        if isinstance(models, list):
            for item in models:
                if item == model_id:
                    return True
                if isinstance(item, dict) and item.get('id') == model_id:
                    return True
        return False

    def get_runtime_model_status(self, provider_id, model_id, provider_map=RUNTIME_PROVIDER_MAP_UNSET):
        if not self.server_base_url:
            return {
                'runtime_checked': True,
                'runtime_available': True,
                'runtime_status': 'ready',
            }

        if provider_map is RUNTIME_PROVIDER_MAP_UNSET:
            provider_map = self.fetch_runtime_provider_map_safe()

        if provider_map is None:
            return {
                'runtime_checked': False,
                'runtime_available': False,
                'runtime_status': 'unknown',
            }

        provider_info = provider_map.get(provider_id) or {}
        runtime_available = self._runtime_provider_has_model(provider_info, model_id)
        return {
            'runtime_checked': True,
            'runtime_available': runtime_available,
            'runtime_status': 'ready' if runtime_available else 'restart_required',
        }

    def get_selection_runtime_status(self, selected_model_provider_id='', provider_map=RUNTIME_PROVIDER_MAP_UNSET):
        model_target = self._resolve_model_target(selected_model_provider_id)
        status = self.get_runtime_model_status(
            model_target['provider_id'],
            model_target['model_id'],
            provider_map=provider_map,
        )
        return {
            **status,
            'provider_id': model_target['provider_id'],
            'model_id': model_target['model_id'],
            'variant': model_target.get('variant') or '',
        }

    def _assert_runtime_model_available(self, provider_id, model_id, selected_model_provider_id=''):
        if not self.server_base_url or not selected_model_provider_id:
            return

        runtime_status = self.get_runtime_model_status(provider_id, model_id)
        if runtime_status['runtime_available']:
            return

        OpencodeConfigSyncService.sync()
        raise RuntimeError(
            f'所选助手模型 {provider_id}/{model_id} 已写入 opencode 配置文件，但当前 opencode serve 尚未加载它。请重启 opencode serve 后重试。'
        )

    def _resolve_model_target(self, selected_model_provider_id=''):
        if selected_model_provider_id:
            builtin_model = BuiltinAgentModelRegistry.get_model(selected_model_provider_id)
            if builtin_model:
                return {
                    'provider_id': builtin_model['provider_id'],
                    'model_id': builtin_model['model_id'],
                    'variant': builtin_model.get('variant') or '',
                }

            provider = ModelProvider.objects.filter(
                id=selected_model_provider_id,
                provider_type='llm',
                is_active=True,
            ).first()
            if provider:
                runtime_target = OpencodeConfigSyncService.build_runtime_target(provider)
                return {
                    'provider_id': runtime_target['provider_id'],
                    'model_id': runtime_target['model_id'],
                    'variant': runtime_target.get('variant') or '',
                }

        return {
            'provider_id': self.model_provider_id,
            'model_id': self.model_id,
            'variant': self.model_variant,
        }

    def _build_prompt_payload(self, user_message, context, ui_context, selected_model_provider_id='', include_agent=True):
        model_target = self._resolve_model_target(selected_model_provider_id)
        self._assert_runtime_model_available(
            model_target['provider_id'],
            model_target['model_id'],
            selected_model_provider_id=selected_model_provider_id,
        )
        payload = {
            'model': {
                'providerID': model_target['provider_id'],
                'modelID': model_target['model_id'],
            },
            'system': self._build_system_prompt(context, ui_context),
            'parts': self._build_message_parts(user_message),
            'noReply': False,
        }
        if model_target['variant']:
            payload['variant'] = model_target['variant']
        if include_agent and self.agent_name:
            payload['agent'] = self.agent_name
        return payload

    def _should_retry_without_agent(self, error):
        if not self.agent_name:
            return False

        response = getattr(error, 'response', None)
        if response is None:
            return False

        try:
            payload = response.json() or {}
            message = json.dumps(payload, ensure_ascii=False)
        except ValueError:
            message = response.text or ''

        normalized = message.lower()
        schema_markers = (
            'invalid json payload',
            'unknown name "ref"',
            "unknown name '$ref'",
            'function_declarations',
            'function declarations',
            'tools[',
        )
        return any(marker in normalized for marker in schema_markers)

    def _submit_prompt(self, client, remote_session_id, user_message, context, ui_context, selected_model_provider_id=''):
        try:
            response = client.post(
                f'{self.server_base_url}/session/{remote_session_id}/prompt_async',
                params=self._query_params(),
                json=self._build_prompt_payload(
                    user_message,
                    context,
                    ui_context,
                    selected_model_provider_id=selected_model_provider_id,
                    include_agent=True,
                ),
                timeout=30,
            )
            response.raise_for_status()
            return
        except requests.HTTPError as error:
            if not self._should_retry_without_agent(error):
                raise

        retry_response = client.post(
            f'{self.server_base_url}/session/{remote_session_id}/prompt_async',
            params=self._query_params(),
            json=self._build_prompt_payload(
                user_message,
                context,
                ui_context,
                selected_model_provider_id=selected_model_provider_id,
                include_agent=False,
            ),
            timeout=30,
        )
        retry_response.raise_for_status()

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

    def stream_response(self, *, session, user_message, context, ui_context=None, selected_model_provider_id='', manager=None, user_id=None, scope_key=None):
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

        self._submit_prompt(
            client,
            remote_session_id,
            user_message,
            context,
            ui_context,
            selected_model_provider_id=selected_model_provider_id,
        )

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
                    if part.get('type') == 'step-start':
                        yield {'type': 'status', 'status': '正在整理回答...'}
                        continue
                    if part.get('type') == 'tool':
                        tool_name = part.get('tool') or '工具'
                        yield {'type': 'status', 'status': f'正在调用 {tool_name}...'}
                        continue
                    if part.get('type') == 'reasoning':
                        yield {'type': 'status', 'status': '正在分析当前问题...'}
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
        try:
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
        except requests.exceptions.ReadTimeout:
            return
        except requests.exceptions.ConnectionError as exc:
            if 'Read timed out' not in str(exc):
                raise
            return

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
