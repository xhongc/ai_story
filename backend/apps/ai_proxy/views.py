"""
AI 代理视图
职责: 统一代理模型列表、LLM、图片和视频请求，复用 ai_story 的鉴权与 ModelProvider 配置
"""

import time
import uuid
import logging
from typing import Any, Dict, List, Optional

import requests
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.models.models import ModelProvider
from apps.models.serializers import ModelProviderListSerializer
from core.ai_client.base import AIResponse
from core.ai_client.factory import create_ai_client
from core.ai_client.image_service import ImageGenerationService
from core.ai_client.schemas import ImageEditRequest, Text2ImageRequest
from core.utils.file_storage import image_storage, video_storage

logger = logging.getLogger(__name__)


PROVIDER_TYPE_LABELS = {
    'llm': 'LLM',
    'text2image': '文生图',
    'image2video': '视频',
    'image_edit': '图片编辑',
}

MODEL_CATEGORY_DEFINITIONS = [
    {
        'key': 'chat',
        'title': '对话模型',
        'description': '文本对话、问答与推理',
        'icon_name': 'Bot',
        'provider_type': 'llm',
    },
    {
        'key': 'image',
        'title': '图像生成模型',
        'description': '文生图与参考图生成',
        'icon_name': 'Image',
        'provider_type': 'text2image',
    },
    {
        'key': 'video',
        'title': '视频生成模型',
        'description': '图生视频与动态内容生成',
        'icon_name': 'Video',
        'provider_type': 'image2video',
    },
    {
        'key': 'image_edit',
        'title': '图片编辑模型',
        'description': '局部重绘、修复与图像增强',
        'icon_name': 'Palette',
        'provider_type': 'image_edit',
    },
]


def _ensure_list(value: Any) -> List[Any]:
    """将输入统一转换为列表。"""
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """安全解析整数。"""
    if value in (None, ''):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """安全解析浮点数。"""
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_size(value: Any) -> Dict[str, Optional[int]]:
    """解析 `1024x1024` 风格尺寸。"""
    if not value or not isinstance(value, str) or 'x' not in value.lower():
        return {'width': None, 'height': None}

    width_str, height_str = value.lower().split('x', 1)
    return {
        'width': _parse_int(width_str),
        'height': _parse_int(height_str),
    }


def _build_provider_payload(provider: ModelProvider) -> Dict[str, Any]:
    """构造响应中的 provider 摘要。"""
    return {
        'id': str(provider.id),
        'name': provider.name,
        'provider_type': provider.provider_type,
        'provider_type_display': provider.get_provider_type_display(),
        'model_name': provider.model_name,
    }


def _pick_provider(provider_type: str, model: str = '') -> Optional[ModelProvider]:
    """按模型名或 provider id 解析当前要使用的模型配置。"""
    queryset = ModelProvider.objects.filter(
        provider_type=provider_type,
        is_active=True,
    ).order_by('-priority', '-created_at')

    if model:
        provider = queryset.filter(model_name=model).first()
        if provider:
            return provider

        try:
            provider = queryset.filter(id=model).first()
            if provider:
                return provider
        except (ValueError, TypeError):
            pass

    return queryset.first()


class AIModelsView(APIView):
    """
    统一模型列表接口
    GET /api/v1/ai/models
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        provider_map = {}
        categories = []

        for category in MODEL_CATEGORY_DEFINITIONS:
            providers = ModelProvider.objects.filter(
                provider_type=category['provider_type'],
                is_active=True,
            ).order_by('-priority', '-created_at')
            serialized = ModelProviderListSerializer(providers, many=True).data
            provider_map[category['key']] = serialized
            categories.append({
                **category,
                'count': len(serialized),
                'items': serialized,
            })

        return Response({
            **provider_map,
            'categories': categories,
        })


class ChatCompletionsProxyView(APIView):
    """
    LLM 代理接口
    POST /api/v1/ai/chat/completions
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        model = request.data.get('model', '')
        messages = request.data.get('messages', [])
        temperature = request.data.get('temperature', 0.7)
        max_tokens = request.data.get('max_tokens', 2000)

        if not messages:
            return Response(
                {'error': 'messages 不能为空'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = _pick_provider('llm', model)
        if not provider:
            return Response(
                {'error': '没有可用的 LLM 模型提供商，请在 ai_story 后台配置 ModelProvider'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        headers = {
            'Authorization': f'Bearer {provider.api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': provider.model_name,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False,
        }

        try:
            start_time = time.time()
            upstream_response = requests.post(
                provider.api_url,
                headers=headers,
                json=payload,
                timeout=provider.timeout,
            )
            latency_ms = int((time.time() - start_time) * 1000)

            if upstream_response.status_code != 200:
                logger.error(
                    '上游 LLM 请求失败: status=%s provider=%s body=%s',
                    upstream_response.status_code,
                    provider.name,
                    upstream_response.text[:300],
                )
                return Response(
                    {'error': f'上游 API 请求失败: {upstream_response.status_code}'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            result = upstream_response.json()
            if 'id' not in result:
                result['id'] = f'chatcmpl-{uuid.uuid4().hex[:8]}'
            result.setdefault('model', provider.model_name)
            result.setdefault('metadata', {})
            result['metadata'].update({
                'latency_ms': latency_ms,
                'provider': _build_provider_payload(provider),
            })
            return Response(result)

        except requests.Timeout:
            return Response(
                {'error': '上游 API 请求超时'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            logger.error('LLM 代理异常: %s', exc, exc_info=True)
            return Response(
                {'error': f'代理请求失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ImagesGenerationsProxyView(APIView):
    """
    图片统一代理接口
    POST /api/v1/ai/images/generations
    """

    permission_classes = [permissions.IsAuthenticated]

    def _resolve_provider_type(self, request) -> str:
        mode = str(request.data.get('mode', '') or request.data.get('edit_mode', '')).lower()
        source_images = _ensure_list(
            request.data.get('image') or request.data.get('images') or request.data.get('source_images')
        )
        mask = request.data.get('mask') or request.data.get('mask_image')

        if mode in {'inpaint', 'img2img', 'image_edit', 'edit'}:
            return 'image_edit'
        if mask:
            return 'image_edit'
        if request.data.get('provider_type') == 'image_edit':
            return 'image_edit'
        if source_images and request.data.get('force_edit') is True:
            return 'image_edit'
        return 'text2image'

    def _build_request_context(self, request) -> Dict[str, Any]:
        size = _parse_size(request.data.get('size'))
        width = _parse_int(request.data.get('width'), size['width'])
        height = _parse_int(request.data.get('height'), size['height'])
        reference_images = _ensure_list(
            request.data.get('image') or request.data.get('images') or request.data.get('source_images')
        )
        payload_model = request.data.get('model', '')

        return {
            'model': payload_model,
            'prompt': request.data.get('prompt', ''),
            'negative_prompt': request.data.get('negative_prompt', ''),
            'mask': request.data.get('mask') or request.data.get('mask_image') or '',
            'width': width,
            'height': height,
            'reference_images': reference_images,
            'aspect_ratio': request.data.get('aspect_ratio') or request.data.get('ratio') or '',
            'sample_count': _parse_int(request.data.get('n'), _parse_int(request.data.get('sample_count'), 1)) or 1,
            'seed': _parse_int(request.data.get('seed')),
            'strength': _parse_float(request.data.get('strength'), 0.35) or 0.35,
            'mode': request.data.get('mode') or request.data.get('edit_mode') or '',
            'extra': {
                key: value for key, value in request.data.items()
                if key not in {
                    'model', 'prompt', 'negative_prompt', 'mask', 'mask_image', 'width', 'height',
                    'image', 'images', 'source_images', 'aspect_ratio', 'ratio', 'n', 'sample_count',
                    'seed', 'strength', 'mode', 'edit_mode', 'size', 'provider_type', 'force_edit',
                }
            },
        }

    def _normalize_image_result(
        self,
        result: AIResponse,
        provider: ModelProvider,
        provider_type: str,
    ) -> Response:
        if not result.success:
            return Response(
                {'error': result.error or '图片生成失败'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            'id': f'imggen-{uuid.uuid4().hex[:8]}',
            'object': 'list',
            'created': int(time.time()),
            'model': provider.model_name,
            'provider': _build_provider_payload(provider),
            'provider_type': provider_type,
            'data': result.data if isinstance(result.data, list) else _ensure_list(result.data),
            'text': result.text,
            'metadata': result.metadata,
        })

    def post(self, request):
        provider_type = self._resolve_provider_type(request)
        context = self._build_request_context(request)

        if not context['prompt']:
            return Response(
                {'error': 'prompt 不能为空'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = _pick_provider(provider_type, context['model'])
        if not provider:
            return Response(
                {'error': f'没有可用的 {PROVIDER_TYPE_LABELS.get(provider_type, provider_type)} 模型提供商'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            client = create_ai_client(provider)
            if provider_type == 'image_edit':
                ai_response = ImageGenerationService.edit(
                    provider,
                    ImageEditRequest(
                        source_images=context['reference_images'],
                        prompt=context['prompt'],
                        mask_image=context['mask'],
                        negative_prompt=context['negative_prompt'],
                        strength=context['strength'],
                        width=context['width'],
                        height=context['height'],
                        edit_mode=context['mode'] or 'img2img',
                        extra=context['extra'],
                    ),
                    client=client,
                )
            else:
                ai_response = ImageGenerationService.generate(
                    provider,
                    Text2ImageRequest(
                        prompt=context['prompt'],
                        negative_prompt=context['negative_prompt'],
                        reference_images=context['reference_images'],
                        width=context['width'],
                        height=context['height'],
                        aspect_ratio=context['aspect_ratio'],
                        sample_count=context['sample_count'],
                        seed=context['seed'],
                        extra=context['extra'],
                    ),
                    client=client,
                )
            return self._normalize_image_result(ai_response, provider, provider_type)
        except Exception as exc:
            logger.error('图片代理异常: %s', exc, exc_info=True)
            return Response(
                {'error': f'图片代理请求失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VideosGenerationsProxyView(APIView):
    """
    视频统一代理接口
    POST /api/v1/ai/videos/generations
    """

    permission_classes = [permissions.IsAuthenticated]

    def _normalize_video_result(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, AIResponse):
            return {
                'success': result.success,
                'data': result.data if isinstance(result.data, list) else _ensure_list(result.data),
                'metadata': result.metadata,
                'error': result.error,
            }

        if isinstance(result, dict):
            normalized_data = result.get('data', [])
            if not isinstance(normalized_data, list):
                normalized_data = _ensure_list(normalized_data)
            return {
                'success': result.get('success', True),
                'data': normalized_data,
                'metadata': result.get('metadata', {}),
                'error': result.get('error'),
            }

        return {
            'success': False,
            'data': [],
            'metadata': {},
            'error': '无法识别的视频响应格式',
        }

    def post(self, request):
        prompt = request.data.get('prompt', '')
        model = request.data.get('model', '')
        image_input = request.data.get('image_url') or request.data.get('image')
        image_base64 = request.data.get('image_base64')
        if isinstance(image_input, str) and image_input.startswith('data:') and ';base64,' in image_input and not image_base64:
            image_base64 = image_input.split(';base64,', 1)[1]
            image_input = ''

        if not prompt:
            return Response(
                {'error': 'prompt 不能为空'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = _pick_provider('image2video', model)
        if not provider:
            return Response(
                {'error': '没有可用的视频模型提供商'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            client = create_ai_client(provider)
            raw_result = client._generate_video(
                prompt=prompt,
                model=provider.model_name,
                image_uri=image_input,
                image_base64=image_base64,
                image_mime_type=request.data.get('image_mime_type', 'image/jpeg'),
                duration_seconds=_parse_int(request.data.get('duration_seconds'), _parse_int(request.data.get('duration'), 5)) or 5,
                sample_count=_parse_int(request.data.get('sample_count'), _parse_int(request.data.get('n'), 1)) or 1,
                aspect_ratio=request.data.get('aspect_ratio') or request.data.get('ratio') or '16:9',
                resolution=request.data.get('resolution'),
                seed=_parse_int(request.data.get('seed')),
                negative_prompt=request.data.get('negative_prompt'),
                generate_audio=request.data.get('generate_audio', True),
                camera_movement_description=(
                    request.data.get('camera_movement_description')
                    or request.data.get('cameraMovementDescription')
                    or ''
                ),
            )
            result = self._normalize_video_result(raw_result)
            if not result['success']:
                return Response(
                    {'error': result['error'] or '视频生成失败'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return Response({
                'id': f'vidgen-{uuid.uuid4().hex[:8]}',
                'object': 'list',
                'created': int(time.time()),
                'model': provider.model_name,
                'provider': _build_provider_payload(provider),
                'data': result['data'],
                'metadata': result['metadata'],
            })
        except Exception as exc:
            logger.error('视频代理异常: %s', exc, exc_info=True)
            return Response(
                {'error': f'视频代理请求失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FileUploadView(APIView):
    """
    文件上传接口
    POST /api/v1/ai/files/upload
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': '请上传文件（字段名: file）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = file.content_type or ''
        filename = file.name

        try:
            file_content = file.read()

            if content_type.startswith('image/'):
                _, relative_path = image_storage.save_file(filename, file_content)
                url_path = f'storage/image/{relative_path}'
            else:
                _, relative_path = video_storage.save_file(filename, file_content)
                url_path = f'storage/video/{relative_path}'

            scheme = request.scheme
            host = request.get_host()
            file_url = f'{scheme}://{host}/{url_path}'

            return Response({
                'id': f'file-{uuid.uuid4().hex[:8]}',
                'filename': filename,
                'url': file_url,
                'size': len(file_content),
                'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }, status=status.HTTP_201_CREATED)

        except Exception as exc:
            logger.error('文件上传失败: %s', exc, exc_info=True)
            return Response(
                {'error': f'文件上传失败: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
