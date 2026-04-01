import json
import uuid

from django.contrib.auth import get_user_model
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .services.context_builder import AgentContextBuilder
from .services.gateway import AgentGateway
from .services.session_manager import AgentSessionManager


class AgentStreamAuthMixin:
    def _authenticate_stream_user(self, request):
        token = (request.query_params.get('access_token') or '').strip()
        if not token:
            return None

        try:
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            if not user_id:
                return None
            return get_user_model().objects.filter(id=user_id).first()
        except Exception:
            return None


class AgentSessionInitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scope_key = (request.data.get('scope_key') or '').strip()
        route_name = (request.data.get('route_name') or '').strip()
        route_params = request.data.get('route_params') or {}
        ui_context = request.data.get('ui_context') or {}

        if not scope_key:
            return Response({'error': '缺少 scope_key'}, status=status.HTTP_400_BAD_REQUEST)

        manager = AgentSessionManager()
        _, created = manager.init_session(
            user_id=request.user.id,
            scope_key=scope_key,
            route_name=route_name,
            route_params=route_params,
            ui_context=ui_context,
        )

        return Response({
            'scope_key': scope_key,
            'created': created,
            'stream_url': f'/api/v1/agent/session/{scope_key}/stream/',
        })


class AgentSessionMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, scope_key):
        text = (request.data.get('text') or '').strip()
        ui_context = request.data.get('ui_context') or {}
        if not text:
            return Response({'error': '缺少 text'}, status=status.HTTP_400_BAD_REQUEST)

        manager = AgentSessionManager()
        session, _ = manager.init_session(
            user_id=request.user.id,
            scope_key=scope_key,
            route_name=(request.data.get('route_name') or '').strip(),
            route_params=request.data.get('route_params') or {},
            ui_context=ui_context,
        )
        manager.append_message(request.user.id, scope_key, 'user', text)

        stream_token = uuid.uuid4().hex
        manager.save_stream_payload(stream_token, {
            'scope_key': scope_key,
            'user_id': request.user.id,
            'text': text,
            'ui_context': ui_context or session.get('ui_context') or {},
        })

        return Response({
            'accepted': True,
            'stream_token': stream_token,
        })


class AgentSessionStreamView(APIView, AgentStreamAuthMixin):
    permission_classes = [AllowAny]

    def get(self, request, scope_key):
        user = self._authenticate_stream_user(request)
        if not user:
            return Response({'error': '未授权访问'}, status=status.HTTP_401_UNAUTHORIZED)

        stream_token = (request.query_params.get('stream_token') or '').strip()
        if not stream_token:
            return Response({'error': '缺少 stream_token'}, status=status.HTTP_400_BAD_REQUEST)

        manager = AgentSessionManager()
        stream_payload = manager.get_stream_payload(stream_token)
        if not stream_payload:
            return Response({'error': '流式令牌无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)
        if stream_payload.get('user_id') != user.id or stream_payload.get('scope_key') != scope_key:
            return Response({'error': '无权访问该流式会话'}, status=status.HTTP_403_FORBIDDEN)

        session = manager.snapshot_session(user.id, scope_key)
        if not session:
            return Response({'error': '会话不存在'}, status=status.HTTP_404_NOT_FOUND)

        context_builder = AgentContextBuilder()
        gateway = AgentGateway()

        def event_stream():
            final_message = ''
            try:
                context = context_builder.build(
                    user=user,
                    scope_key=scope_key,
                    route_name=session.get('route_name') or '',
                    route_params=session.get('route_params') or {},
                    ui_context=stream_payload.get('ui_context') or session.get('ui_context') or {},
                )

                for event in gateway.stream_response(
                    session=session,
                    user_message=stream_payload.get('text') or '',
                    context=context,
                    ui_context=stream_payload.get('ui_context') or session.get('ui_context') or {},
                    manager=manager,
                    user_id=user.id,
                    scope_key=scope_key,
                ):
                    if event.get('type') == 'message':
                        final_message = event.get('content') or ''
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
            finally:
                if final_message:
                    manager.append_message(user.id, scope_key, 'assistant', final_message)
                manager.delete_stream_payload(stream_token)

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
        response['Cache-Control'] = 'no-cache, no-transform'
        response['X-Accel-Buffering'] = 'no'
        return response


class AgentSessionUiResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, scope_key):
        action_id = (request.data.get('action_id') or '').strip()
        intent = (request.data.get('intent') or '').strip()
        success = bool(request.data.get('success'))
        result = request.data.get('result') or ''

        manager = AgentSessionManager()
        manager.append_message(
            request.user.id,
            scope_key,
            'tool',
            result or f'{intent or action_id} 已执行',
            extra={
                'action_id': action_id,
                'intent': intent,
                'success': success,
            }
        )
        return Response({'accepted': True})


class AgentSessionAbortView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, scope_key):
        manager = AgentSessionManager()
        session = manager.snapshot_session(request.user.id, scope_key)
        remote_session_id = (session or {}).get('agent_session_id')
        if remote_session_id:
            gateway = AgentGateway()
            try:
                gateway.abort_session(remote_session_id)
            except Exception:
                pass
        return Response({'accepted': True})
