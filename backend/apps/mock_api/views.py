"""Django views that expose the mock AI capabilities through HTTP endpoints."""

import json
import logging
import time
import uuid
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from django.http import StreamingHttpResponse
from django.urls import reverse
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.ai_client.mock_llm_client import MockLLMClient
from core.ai_client.mock_text2image_client import MockText2ImageClient
from core.ai_client.mock_image2video_client import MockImage2VideoClient

logger = logging.getLogger(__name__)


DEFAULT_CAMERA_MOVEMENT: Dict[str, Any] = {
    "movement_type": "slow_zoom_in",
    "movement_params": {
        "start_scale": 1.0,
        "end_scale": 1.2,
        "duration": 3.0,
        "easing": "ease_in_out",
    },
    "description": "缓慢推进镜头，聚焦主体",
}


class MockAPIBaseView(APIView):
    """Base view that configures permissions and helper methods."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def _serialize_response(self, ai_response) -> Dict[str, Any]:
        """Convert AIResponse dataclass to a serializable dict."""
        return asdict(ai_response)

    def _error_response(self, message: str, status_code=status.HTTP_400_BAD_REQUEST) -> Response:
        """Return a normalized error payload."""
        return Response(
            {
                'success': False,
                'error': message,
                'data': {},
                'metadata': {},
            },
            status=status_code,
        )

    def _build_api_url(self, request) -> str:
        """Return the canonical base URL for the mock API."""
        return request.build_absolute_uri('/api/mock').rstrip('/')

    @staticmethod
    def _get_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {'1', 'true', 'yes', 'on'}
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def perform_content_negotiation(self, request, force=False):
        """
        Allow text/event-stream Accept headers even though DRF has no renderer for them.
        The actual streaming responses use StreamingHttpResponse and bypass renderers.
        """
        try:
            return super().perform_content_negotiation(request, force)
        except exceptions.NotAcceptable:
            accept_header = request.META.get('HTTP_ACCEPT', '')
            if 'text/event-stream' in accept_header:
                renderer = self.renderer_classes[0]()
                return (renderer, renderer.media_type)
            raise


class MockAPIRootView(MockAPIBaseView):
    """Expose meta information about all available mock endpoints."""

    def _build_payload(self, request):
        base_url = request.build_absolute_uri(reverse('mock_api:root'))
        return Response(
            {
                'service': 'AI Story Mock API',
                'description': '模拟 LLM、文生图、图生视频能力的调试端点',
                'base_url': base_url.rstrip('/'),
                'endpoints': {
                    'llm': request.build_absolute_uri(reverse('mock_api:llm_generate')),
                    'text2image': request.build_absolute_uri(reverse('mock_api:text2image_generate')),
                    'image2video': request.build_absolute_uri(reverse('mock_api:image2video_generate')),
                },
            }
        )

    def get(self, request):
        return self._build_payload(request)

    def post(self, request):
        """Allow POST so callers hitting /api/mock/ get consistent information."""
        return self._build_payload(request)


class MockLLMGenerateView(MockAPIBaseView):
    """HTTP endpoint compatible with the mock LLM client."""

    def post(self, request):
        prompt = (request.data.get('prompt') or "").strip()
        

        max_tokens = self._get_int(request.data.get('max_tokens'), 500)
        temperature = self._get_float(request.data.get('temperature'), 0.7)
        model_name = request.data.get('model_name') or 'mock-llm-v1'
        api_key = request.data.get('api_key') or 'mock-api-key-not-required'
        stream = (
            self._get_bool(request.data.get('stream'))
            or self._get_bool(request.query_params.get('stream'))
        )

        client = MockLLMClient(
            api_url=self._build_api_url(request),
            api_key=api_key,
            model_name=model_name,
        )

        try:
            if stream:
                return self._stream_llm_response(
                    client,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model_name=model_name,
                )

            ai_response = async_to_sync(client.generate)(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Mock LLM 生成失败: %s", exc)
            return self._error_response(
                f"LLM生成失败: {exc}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(self._serialize_response(ai_response))

    def _stream_llm_response(
        self,
        client: MockLLMClient,
        prompt: str,
        max_tokens: int,
        temperature: float,
        model_name: str,
    ) -> StreamingHttpResponse:
        """Return a StreamingHttpResponse emitting OpenAI-compatible SSE data."""

        def event_stream():
            chunk_id = f"mock-chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())
            try:
                for chunk in client.generate_stream(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    if chunk.get('type') == 'token':
                        payload = self._build_stream_payload(
                            chunk_id,
                            created,
                            model_name,
                            content=chunk.get('content', ''),
                            finish_reason=None,
                        )
                        yield self._format_sse(payload)
                    elif chunk.get('type') == 'done':
                        payload = self._build_stream_payload(
                            chunk_id,
                            created,
                            model_name,
                            content="",
                            finish_reason=chunk.get('metadata', {}).get('finish_reason', 'stop'),
                        )
                        yield self._format_sse(payload)
                yield b"data: [DONE]\n\n"
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Mock LLM 流式生成失败: %s", exc)
                payload = self._build_stream_payload(
                    chunk_id,
                    created,
                    model_name,
                    content="",
                    finish_reason="error",
                    error=str(exc),
                )
                yield self._format_sse(payload)
                yield b"data: [DONE]\n\n"

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream; charset=utf-8',
        )

    @staticmethod
    def _build_stream_payload(
        chunk_id: str,
        created: int,
        model_name: str,
        content: str,
        finish_reason: Optional[str],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        delta: Dict[str, Any] = {'content': content}
        if error:
            delta['error'] = error
        return {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': created,
            'model': model_name,
            'choices': [
                {
                    'index': 0,
                    'delta': delta,
                    'finish_reason': finish_reason,
                }
            ],
        }

    @staticmethod
    def _format_sse(payload: Dict[str, Any]) -> bytes:
        """Format payload as SSE data bytes."""
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode('utf-8')


class MockText2ImageGenerateView(MockAPIBaseView):
    """Expose the mock text-to-image behaviour over HTTP."""

    def post(self, request):
        prompt = (request.data.get('prompt') or "").strip()
        if not prompt:
            return self._error_response("prompt 字段不能为空")

        width = self._get_int(request.data.get('width'), 1024)
        height = self._get_int(request.data.get('height'), 1024)
        steps = self._get_int(request.data.get('steps'), 20)
        sample_count = self._get_int(request.data.get('sample_count'), 1)
        ratio = request.data.get('ratio') or '1:1'
        resolution = request.data.get('resolution') or '2k'
        negative_prompt = request.data.get('negative_prompt') or ''
        model_name = request.data.get('model_name') or 'mock-text2image-v1'
        api_key = request.data.get('api_key') or 'mock-api-key-not-required'

        client = MockText2ImageClient(
            api_url=self._build_api_url(request),
            api_key=api_key,
            model_name=model_name,
        )

        try:
            ai_response = client.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                sample_count=sample_count,
                ratio=ratio,
                resolution=resolution,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Mock 文生图生成失败: %s", exc)
            return self._error_response(
                f"文生图生成失败: {exc}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(self._serialize_response(ai_response))


class MockImage2VideoGenerateView(MockAPIBaseView):
    """Expose the mock image-to-video behaviour over HTTP."""

    def post(self, request):
        image_url = (request.data.get('image_url') or "").strip()
        if not image_url:
            return self._error_response("image_url 字段不能为空")

        camera_movement = request.data.get('camera_movement')
        if not isinstance(camera_movement, dict):
            camera_movement = deepcopy(DEFAULT_CAMERA_MOVEMENT)

        duration = self._get_float(request.data.get('duration'), 3.0)
        fps = self._get_int(request.data.get('fps'), 24)
        width = self._get_int(request.data.get('width'), 1280)
        height = self._get_int(request.data.get('height'), 720)
        model_name = request.data.get('model_name') or 'mock-image2video-v1'
        api_key = request.data.get('api_key') or 'mock-api-key-not-required'

        client = MockImage2VideoClient(
            api_url=self._build_api_url(request),
            api_key=api_key,
            model_name=model_name,
        )

        try:
            ai_response = async_to_sync(client.generate)(
                image_url=image_url,
                camera_movement=camera_movement,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Mock 图生视频生成失败: %s", exc)
            return self._error_response(
                f"图生视频生成失败: {exc}",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(self._serialize_response(ai_response))
