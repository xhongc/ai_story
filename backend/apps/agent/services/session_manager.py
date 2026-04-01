from copy import deepcopy

from django.core.cache import cache
from django.utils import timezone


SESSION_PREFIX = 'agent_session'
STREAM_PREFIX = 'agent_stream'


def _session_key(user_id, scope_key):
    return f'{SESSION_PREFIX}:{user_id}:{scope_key}'


def _stream_key(stream_token):
    return f'{STREAM_PREFIX}:{stream_token}'


class AgentSessionManager:
    session_timeout = 24 * 60 * 60
    stream_timeout = 5 * 60

    def get_session(self, user_id, scope_key):
        return cache.get(_session_key(user_id, scope_key)) or None

    def save_session(self, user_id, scope_key, payload):
        cache.set(_session_key(user_id, scope_key), payload, timeout=self.session_timeout)
        return payload

    def update_session(self, user_id, scope_key, **fields):
        session = self.get_session(user_id, scope_key) or {}
        session.update(fields)
        session['updated_at'] = timezone.now().isoformat()
        self.save_session(user_id, scope_key, session)
        return session

    def init_session(self, user_id, scope_key, route_name='', route_params=None, ui_context=None):
        existing = self.get_session(user_id, scope_key)
        created = False

        if not existing:
            existing = {
                'scope_key': scope_key,
                'route_name': route_name or '',
                'route_params': route_params or {},
                'ui_context': ui_context or {},
                'messages': [],
                'created_at': timezone.now().isoformat(),
                'updated_at': timezone.now().isoformat(),
                'agent_session_id': None,
            }
            created = True
        else:
            existing['route_name'] = route_name or existing.get('route_name', '')
            existing['route_params'] = route_params or existing.get('route_params', {})
            existing['ui_context'] = ui_context or existing.get('ui_context', {})
            existing['updated_at'] = timezone.now().isoformat()

        self.save_session(user_id, scope_key, existing)
        return existing, created

    def append_message(self, user_id, scope_key, role, content, extra=None):
        session = self.get_session(user_id, scope_key) or {}
        messages = list(session.get('messages') or [])
        messages.append({
            'role': role,
            'content': content,
            'extra': extra or {},
            'created_at': timezone.now().isoformat(),
        })
        session['messages'] = messages[-20:]
        session['updated_at'] = timezone.now().isoformat()
        self.save_session(user_id, scope_key, session)
        return session

    def save_stream_payload(self, stream_token, payload):
        cache.set(_stream_key(stream_token), payload, timeout=self.stream_timeout)

    def get_stream_payload(self, stream_token):
        return cache.get(_stream_key(stream_token)) or None

    def delete_stream_payload(self, stream_token):
        cache.delete(_stream_key(stream_token))

    def snapshot_session(self, user_id, scope_key):
        session = self.get_session(user_id, scope_key)
        return deepcopy(session) if session else None
