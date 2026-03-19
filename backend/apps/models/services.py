"""
模型管理服务层
职责: 处理模型提供商相关业务逻辑
遵循单一职责原则(SRP)和依赖倒置原则(DIP)
"""

import inspect
import requests
from typing import Dict, Any, Optional, List, Iterable
from django.db import transaction
from django.db.models import Q, Avg, Sum
from asgiref.sync import sync_to_async
from .models import ModelProvider, ModelUsageLog
from .vendor_catalog import VENDOR_CATALOG
from urllib.parse import urlparse


CAPABILITY_LABELS = {
    'llm': '语言模型',
    'vlm': '视觉语言模型',
    'text2image': '文生图',
    'image2video': '图生视频',
    'image_edit': '图片编辑',
}

CAPABILITY_CLASSIFICATION_PATTERNS = {
    'llm': [
        'gpt', 'o1', 'o3', 'o4', 'claude', 'qwen', 'deepseek', 'gemini', 'grok',
        'glm', 'moonshot', 'kimi', 'doubao', 'abab', 'minimax', 'llama', 'mistral',
    ],
    'vlm': [
        'vision', 'vlm', 'multimodal', 'omni', 'gpt-4o', 'gemini-pro-vision', 'qwen-vl',
        'ui-tars', 'see', '-vl', '-VL'
    ],
    'text2image': [
        'gpt-image', 'dall-e', 'dalle', 'flux', 'sdxl', 'stable-diffusion', 'wanx',
        'seedream', 'imagen', 't2i', 'image', 'imagine'
    ],
    'image2video': [
        'video', 'i2v', 'veo', 'kling', 'seedance', 'wan', 's2v',
    ],
    'image_edit': [
        'edit', 'edits', 'inpaint', 'image-edit', 'img2img',
    ],
}

METADATA_CAPABILITY_MAP = {
    'llm': 'llm',
    'chat': 'llm',
    'textgeneration': 'llm',
    'text_generation': 'llm',
    'vlm': 'vlm',
    'multimodal': 'vlm',
    'imagegeneration': 'text2image',
    'text2image': 'text2image',
    'text_to_image': 'text2image',
    'image_generation': 'text2image',
    'videogeneration': 'image2video',
    'image2video': 'image2video',
    'image_to_video': 'image2video',
    'video_generation': 'image2video',
    'imageedit': 'image_edit',
    'imageediting': 'image_edit',
    'image_edit': 'image_edit',
    'inpaint': 'image_edit',
    'embedding': None,
}

EXCLUDED_MODEL_TOKENS = [
    'embedding', 'embbeding', 'vector', 'rerank', 'tts', 'asr', 'speech', 'audio',
    'transcription', 'recognition', 'voice', 'moderation', 'safety',
]


class ModelProviderService:
    """
    模型提供商服务
    职责: 处理模型提供商的业务逻辑
    """

    @staticmethod
    def get_active_providers(provider_type: Optional[str] = None) -> List[ModelProvider]:
        """
        获取激活的模型提供商

        Args:
            provider_type: 提供商类型 (llm, text2image, image2video)

        Returns:
            激活的模型提供商列表
        """
        queryset = ModelProvider.objects.filter(is_active=True)

        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)

        return queryset.order_by('-priority', '-created_at')

    @staticmethod
    def get_provider_by_type_and_priority(
        provider_type: str,
        min_priority: int = 0
    ) -> Optional[ModelProvider]:
        """
        根据类型和优先级获取模型提供商

        Args:
            provider_type: 提供商类型
            min_priority: 最小优先级

        Returns:
            符合条件的最高优先级提供商
        """
        return ModelProvider.objects.filter(
            provider_type=provider_type,
            is_active=True,
            priority__gte=min_priority
        ).order_by('-priority').first()

    @staticmethod
    def search_providers(
        keyword: str,
        provider_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[ModelProvider]:
        """
        搜索模型提供商

        Args:
            keyword: 搜索关键词
            provider_type: 提供商类型
            is_active: 是否激活

        Returns:
            符合条件的提供商列表
        """
        queryset = ModelProvider.objects.all()

        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword) |
                Q(model_name__icontains=keyword) |
                Q(api_url__icontains=keyword)
            )

        # 类型过滤
        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)

        # 激活状态过滤
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset.order_by('-priority', '-created_at')

    @staticmethod
    @transaction.atomic
    def create_provider(data: Dict[str, Any]) -> ModelProvider:
        """
        创建模型提供商

        Args:
            data: 提供商数据

        Returns:
            创建的模型提供商实例
        """
        provider = ModelProvider.objects.create(**data)
        return provider



    @staticmethod
    def _resolve_capability_config(
        vendor: str,
        capability: str,
        api_url_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        vendor_config = VENDOR_CATALOG[vendor]
        capability_config = dict(vendor_config['capabilities'][capability])

        if capability_config.get('configurable_api_url') and api_url_override:
            normalized_api_url = api_url_override.rstrip('/')
            capability_config['api_url'] = normalized_api_url
            path = urlparse(normalized_api_url).path.rstrip('/')
            if path.endswith('/chat/completions'):
                capability_config['models_endpoint'] = normalized_api_url[: -len('/chat/completions')] + '/models'
            elif path.endswith('/images/generations'):
                capability_config['models_endpoint'] = normalized_api_url[: -len('/images/generations')] + '/models'
            elif path.endswith('/images/edits'):
                capability_config['models_endpoint'] = normalized_api_url[: -len('/images/edits')] + '/models'
            elif path.endswith('/videos/generations'):
                capability_config['models_endpoint'] = normalized_api_url[: -len('/videos/generations')] + '/models'
            elif path.endswith('/video/generations'):
                capability_config['models_endpoint'] = normalized_api_url[: -len('/video/generations')] + '/models'
            else:
                capability_config['models_endpoint'] = normalized_api_url.rstrip('/') + '/models'

        return capability_config

    @staticmethod
    def list_builtin_vendors() -> List[Dict[str, Any]]:
        """返回内置厂商目录。"""
        vendors = []
        for key, config in VENDOR_CATALOG.items():
            capabilities = []
            for capability_key, capability in config.get('capabilities', {}).items():
                capabilities.append({
                    'key': capability_key,
                    'provider_type': capability['provider_type'],
                    'api_url': capability['api_url'],
                    'configurable_api_url': capability.get('configurable_api_url', False),
                })
            vendors.append({
                'key': key,
                'label': config['label'],
                'capabilities': capabilities,
            })
        return vendors

    @staticmethod
    def _normalize_capability_token(value: Any) -> str:
        if value is None:
            return ''
        return str(value).strip().lower().replace('-', '').replace(' ', '')

    @staticmethod
    def _iter_metadata_values(value: Any) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            items = []
            for key, item in value.items():
                items.append(str(key))
                items.extend(ModelProviderService._iter_metadata_values(item))
            return items
        if isinstance(value, (list, tuple, set)):
            items = []
            for item in value:
                items.extend(ModelProviderService._iter_metadata_values(item))
            return items
        return [str(value)]

    @staticmethod
    def _should_exclude_model(item: Dict[str, Any], model_key: str) -> bool:
        metadata_values = []
        for field in ('domain', 'task_type', 'modalities', 'features'):
            metadata_values.extend(ModelProviderService._iter_metadata_values(item.get(field)))

        normalized_metadata = [
            ModelProviderService._normalize_capability_token(value)
            for value in metadata_values
        ]
        if any(token in normalized for normalized in normalized_metadata for token in EXCLUDED_MODEL_TOKENS):
            return True

        return any(token in model_key for token in EXCLUDED_MODEL_TOKENS)

    @staticmethod
    def _classify_capability_from_metadata(item: Dict[str, Any]) -> Optional[str]:
        candidates = []
        for field in ('domain', 'task_type', 'modalities', 'features'):
            candidates.extend(ModelProviderService._iter_metadata_values(item.get(field)))

        has_metadata = False
        for candidate in candidates:
            normalized = ModelProviderService._normalize_capability_token(candidate)
            if not normalized:
                continue
            has_metadata = True
            if normalized in METADATA_CAPABILITY_MAP:
                mapped_value = METADATA_CAPABILITY_MAP[normalized]
                return mapped_value if mapped_value is not None else ''

            if 'embedding' in normalized:
                return ''
            if any(keyword in normalized for keyword in ['videogeneration', 'image2video', 'imagetovideo', 'i2v']):
                return 'image2video'
            if any(keyword in normalized for keyword in ['imagegeneration', 'texttoimage', 'text2image', 't2i']):
                return 'text2image'
            if any(keyword in normalized for keyword in ['imageedit', 'imageediting', 'img2img', 'inpaint']):
                return 'image_edit'
            if any(keyword in normalized for keyword in ['vlm', 'multimodal']):
                return 'vlm'
            if any(keyword in normalized for keyword in ['llm', 'chat', 'textgeneration']):
                return 'llm'

        return '' if has_metadata else None

    @staticmethod
    def _classify_capability_from_name(model_key: str, capability: str) -> Optional[str]:
        capability_scores = {
            provider_type: sum(1 for keyword in keywords if keyword in model_key)
            for provider_type, keywords in CAPABILITY_CLASSIFICATION_PATTERNS.items()
        }
        matched_types = [
            provider_type for provider_type, score in capability_scores.items() if score > 0
        ]
        if not matched_types:
            return None
        return max(
            matched_types,
            key=lambda provider_type: (capability_scores[provider_type], provider_type == capability),
        )

    @staticmethod
    def discover_vendor_models(vendor: str, capability: str, api_key: str, api_url: Optional[str] = None) -> Dict[str, Any]:
        """从内置厂商拉取指定能力的模型列表。"""
        vendor_config = VENDOR_CATALOG[vendor]
        capability_config = ModelProviderService._resolve_capability_config(
            vendor,
            capability,
            api_url_override=api_url,
        )
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        response = requests.get(
            capability_config['models_endpoint'],
            headers=headers,
            timeout=20,
        )

        if response.status_code != 200:
            raise ValueError(f'拉取模型列表失败: {response.status_code} - {response.text}')

        payload = response.json()
        models_data = payload.get('data', payload if isinstance(payload, list) else [])

        capability_hints = {
            item.lower()
            for item in (
                capability_config.get('model_filter', []) +
                capability_config.get('recommended_patterns', []) +
                CAPABILITY_CLASSIFICATION_PATTERNS.get(capability, [])
            )
        }

        discovered_models = []
        for item in models_data:
            model_id = str(item.get('id') or item.get('name') or '').strip()
            if not model_id:
                continue

            model_key = model_id.lower()
            if ModelProviderService._should_exclude_model(item, model_key):
                continue
            metadata_capability = ModelProviderService._classify_capability_from_metadata(item)
            if metadata_capability is None:
                classified_capability = ModelProviderService._classify_capability_from_name(model_key, capability)
            else:
                classified_capability = metadata_capability or None

            if classified_capability is not None:
                is_capability_match = classified_capability == capability
            else:
                is_capability_match = any(keyword in model_key for keyword in capability_hints)

            discovered_models.append({
                'id': model_id,
                'name': item.get('name') or model_id,
                'owned_by': item.get('owned_by') or item.get('provider') or '',
                'context_length': item.get('context_length') or item.get('context_window') or None,
                'classified_capability': classified_capability,
                'classified_capability_label': CAPABILITY_LABELS.get(classified_capability, '未分类') if classified_capability else '未分类',
                'is_capability_match': is_capability_match,
                'is_recommended': is_capability_match,
            })

        discovered_models.sort(key=lambda item: (not item['is_capability_match'], item['id']))

        return {
            'vendor': vendor,
            'vendor_label': vendor_config['label'],
            'capability': capability,
            'provider_type': capability_config['provider_type'],
            'api_url': capability_config['api_url'],
            'models': discovered_models,
        }

    @staticmethod
    @transaction.atomic
    def batch_create_vendor_models(data: Dict[str, Any]) -> Dict[str, Any]:
        """批量创建内置厂商模型。"""
        vendor = data['vendor']
        capability = data['capability']
        vendor_config = VENDOR_CATALOG[vendor]
        capability_config = ModelProviderService._resolve_capability_config(
            vendor,
            capability,
            api_url_override=data.get('api_url'),
        )

        base_payload = {
            'provider_type': capability_config['provider_type'],
            'api_url': capability_config['api_url'],
            'api_key': data['api_key'],
            'executor_class': capability_config['executor_class'],
            'max_tokens': data.get('max_tokens', 4096),
            'temperature': data.get('temperature', 0.7),
            'top_p': data.get('top_p', 1.0),
            'timeout': data.get('timeout', 60),
            'is_active': data.get('is_active', True),
            'priority': data.get('priority', 0),
            'rate_limit_rpm': data.get('rate_limit_rpm', 60),
            'rate_limit_rpd': data.get('rate_limit_rpd', 1000),
            'extra_config': {
                'vendor': vendor,
                'vendor_label': vendor_config['label'],
                'vendor_capability': capability,
            },
        }

        created = []
        skipped = []

        for model_name in data['model_names']:
            existing = ModelProvider.objects.filter(
                provider_type=capability_config['provider_type'],
                api_url=capability_config['api_url'],
                model_name=model_name,
            ).first()

            if existing:
                skipped.append({
                    'id': str(existing.id),
                    'name': existing.name,
                    'model_name': existing.model_name,
                    'reason': '模型已存在',
                })
                continue

            provider = ModelProvider.objects.create(
                name=f"{vendor_config['label']} / {model_name}",
                model_name=model_name,
                **base_payload,
            )
            created.append(provider)

        return {
            'vendor': vendor,
            'vendor_label': vendor_config['label'],
            'capability': capability,
            'provider_type': capability_config['provider_type'],
            'created_count': len(created),
            'skipped_count': len(skipped),
            'created': created,
            'skipped': skipped,
        }

    @staticmethod
    @transaction.atomic
    def update_provider(provider_id: str, data: Dict[str, Any]) -> ModelProvider:
        """
        更新模型提供商

        Args:
            provider_id: 提供商ID
            data: 更新数据

        Returns:
            更新后的模型提供商实例
        """
        provider = ModelProvider.objects.get(id=provider_id)

        for key, value in data.items():
            setattr(provider, key, value)

        provider.save()
        return provider

    @staticmethod
    @transaction.atomic
    def delete_provider(provider_id: str) -> bool:
        """
        删除模型提供商

        Args:
            provider_id: 提供商ID

        Returns:
            是否删除成功
        """
        try:
            provider = ModelProvider.objects.get(id=provider_id)
            provider.delete()
            return True
        except ModelProvider.DoesNotExist:
            return False

    @staticmethod
    @transaction.atomic
    def toggle_provider_status(provider_id: str) -> ModelProvider:
        """
        切换模型提供商激活状态

        Args:
            provider_id: 提供商ID

        Returns:
            更新后的模型提供商实例
        """
        provider = ModelProvider.objects.get(id=provider_id)
        provider.is_active = not provider.is_active
        provider.save()
        return provider

    @staticmethod
    def get_provider_statistics(provider_id: str) -> Dict[str, Any]:
        """
        获取模型提供商统计信息

        Args:
            provider_id: 提供商ID

        Returns:
            统计信息字典
        """
        provider = ModelProvider.objects.get(id=provider_id)

        # 总调用次数
        total_count = provider.usage_logs.count()

        # 成功/失败次数
        success_count = provider.usage_logs.filter(status='success').count()
        failed_count = provider.usage_logs.filter(status='failed').count()

        # 成功率
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        # 平均延迟
        avg_latency = provider.usage_logs.aggregate(
            avg=Avg('latency_ms')
        )['avg'] or 0

        # 总Token使用量
        total_tokens = provider.usage_logs.aggregate(
            total=Sum('tokens_used')
        )['total'] or 0

        # 最近7天使用情况
        from django.utils import timezone
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_count = provider.usage_logs.filter(
            created_at__gte=seven_days_ago
        ).count()

        return {
            'total_count': total_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': round(success_rate, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'total_tokens_used': total_tokens,
            'recent_7days_count': recent_count
        }

    @staticmethod
    async def test_provider_connection(
        provider_id: str,
        test_prompt: str = "Hello, this is a test."
    ) -> Dict[str, Any]:
        """
        测试模型提供商连接

        Args:
            provider_id: 提供商ID
            test_prompt: 测试提示词

        Returns:
            测试结果
        """
        import time

        # 使用 sync_to_async 包装同步查询
        provider = await sync_to_async(ModelProvider.objects.get)(id=provider_id)

        if not provider.is_active:
            return {
                'success': False,
                'error': '模型提供商未激活'
            }

        start_time = time.time()

        try:
            # 根据提供商类型选择测试方法
            if provider.provider_type == 'llm':
                result = ModelProviderService._test_llm_provider(
                    provider,
                    test_prompt
                )
            elif provider.provider_type == 'text2image':
                test_prompt = "图片生成：生成一只小狗的照片"
                result = await ModelProviderService._test_text2image_provider(
                    provider,
                    test_prompt
                )
            elif provider.provider_type == 'image2video':
                result = await ModelProviderService._test_image2video_provider(
                    provider,
                    test_prompt,
                )
            elif provider.provider_type == 'image_edit':
                test_prompt = '图片编辑测试：提升图片清晰度并补充细节'
                result = await ModelProviderService._test_image_edit_provider(
                    provider,
                    test_prompt,
                )
            else:
                return {
                    'success': False,
                    'error': f'不支持的提供商类型: {provider.provider_type}'
                }

            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)

            # 记录使用日志
            await sync_to_async(ModelUsageLog.objects.create)(
                model_provider=provider,
                request_data={'test_prompt': test_prompt},
                response_data=result.get('data', {}),
                tokens_used=result.get('tokens_used', 0),
                latency_ms=latency_ms,
                status='success' if result.get('success') else 'failed',
                error_message=result.get('error', '暂无错误') or "暂无错误",
                stage_type='test'
            )

            return {
                'success': result.get('success', False),
                'latency_ms': latency_ms,
                'response': result.get('text', ''),
                'data': result.get('data', {}),
                'error': result.get('error')
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # 记录失败日志
            await sync_to_async(ModelUsageLog.objects.create)(
                model_provider=provider,
                request_data={'test_prompt': test_prompt},
                response_data={},
                latency_ms=latency_ms,
                status='failed',
                error_message=str(e),
                stage_type='test'
            )

            return {
                'success': False,
                'latency_ms': latency_ms,
                'error': str(e)
            }

    @staticmethod
    def _test_llm_provider(
        provider: ModelProvider,
        prompt: str
    ) -> Dict[str, Any]:
        """测试LLM提供商"""
        from core.ai_client.openai_client import OpenAIClient

        client = OpenAIClient(
            api_url=provider.api_url,
            api_key=provider.api_key,
            model_name=provider.model_name,
            max_tokens=min(provider.max_tokens, 100),  # 测试时限制token数
            temperature=provider.temperature,
            timeout=provider.timeout
        )
        full_text = ""
        is_success = False
        for chunk in client.generate_stream(prompt):
            if chunk.get("type") == "done":
                full_text = chunk.get("full_text")
                is_success = True
            elif chunk.get("type") == "error":
                full_text = chunk.get("error")
                is_success = False
        return {
            'success': is_success,
            'text': full_text,
            'data': {
                'prompt': prompt,
                'provider': provider.name
            },
            'tokens_used': 0
        }

    @staticmethod
    async def _test_text2image_provider(
        provider: ModelProvider,
        prompt: str
    ) -> Dict[str, Any]:
        """测试文生图提供商"""
        from core.ai_client.factory import create_ai_client

        extra_config = provider.extra_config or {}
        width = extra_config.get('width', 1024)
        height = extra_config.get('height', 1024)
        steps = extra_config.get('steps', 20)
        negative_prompt = extra_config.get('negative_prompt', '')
        ratio = extra_config.get('default_ratio') or extra_config.get('ratio', '1:1')
        resolution = extra_config.get('default_resolution') or extra_config.get('resolution', '2k')

        client = await sync_to_async(create_ai_client)(provider)
        ai_response = await sync_to_async(client.generate)(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            ratio=ratio,
            resolution=resolution,
        )

        return {
            'success': ai_response.success,
            'text': ai_response.text,
            'data': {
                'prompt': prompt,
                'provider': provider.name,
                'images': ai_response.data,
                'metadata': ai_response.metadata,
            },
            'tokens_used': ai_response.metadata.get('usage', {}).get('total_tokens', 0),
            'error': ai_response.error,
        }

    @staticmethod
    async def _test_image2video_provider(
        provider: ModelProvider,
        prompt: str,
    ) -> Dict[str, Any]:
        """测试图生视频提供商"""
        from core.ai_client.base import AIResponse
        from core.ai_client.comfyui_client import ComfyUIClient
        from core.ai_client.mock_image2video_client import MockImage2VideoClient
        from core.ai_client.image2video_client import VideoGeneratorClient

        extra_config = provider.extra_config or {}
        image_url = (
            extra_config.get('test_image_url')
            or extra_config.get('image_url')
            or extra_config.get('default_image_url')
        )
        if not image_url:
            image_url = "mock"

        duration = extra_config.get('duration', 5)
        fps = extra_config.get('fps', 24)
        negative_prompt = extra_config.get('negative_prompt', '')
        aspect_ratio = extra_config.get('aspect_ratio', '16:9')
        resolution = extra_config.get('resolution')
        poll_interval = extra_config.get('poll_interval', 5)
        max_wait_time = extra_config.get('max_wait_time', provider.timeout)

        executor_class_path = provider.executor_class or provider.get_default_executor()

        if executor_class_path == 'core.ai_client.comfyui_client.ComfyUIClient':
            client = await sync_to_async(ComfyUIClient)(
                api_url=provider.api_url,
                api_key=provider.api_key,
                model_name=provider.model_name,
                timeout=provider.timeout,
                max_tokens=provider.max_tokens,
                temperature=provider.temperature,
                top_p=provider.top_p,
                **extra_config,
            )
            ai_response = await sync_to_async(client._generate_video)(
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration=duration,
                fps=fps,
                image_url=image_url,
            )
        elif executor_class_path == 'core.ai_client.mock_image2video_client.MockImage2VideoClient':
            client = await sync_to_async(MockImage2VideoClient)(
                api_url=provider.api_url,
                api_key=provider.api_key,
                model_name=provider.model_name,
                timeout=provider.timeout,
                max_tokens=provider.max_tokens,
                temperature=provider.temperature,
                top_p=provider.top_p,
                **extra_config,
            )
            ai_response = await sync_to_async(client._generate_video)(
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration=duration,
                fps=fps,
                image_url=image_url,
            )
        elif executor_class_path in (
            'core.ai_client.image2video_client.VideoGeneratorClient',
            'core.ai_client.image2video_client.Image2VideoClient',
        ):
            client = await sync_to_async(VideoGeneratorClient)(
                api_url=provider.api_url,
                api_token=provider.api_key,
                model=provider.model_name,
            )
            generate_kwargs = {
                'prompt': prompt,
                'model': provider.model_name,
                'image_uri': image_url,
                'duration_seconds': duration,
                'aspect_ratio': aspect_ratio,
                'resolution': resolution,
                'negative_prompt': negative_prompt,
                'poll_interval': poll_interval,
                'max_wait_time': max_wait_time,
            }
            generate_kwargs.update(extra_config.get('test_generate_kwargs', {}))

            generate_func = client._generate_video
            signature = inspect.signature(generate_func)
            if 'fps' in signature.parameters:
                generate_kwargs['fps'] = fps

            video_result = await sync_to_async(generate_func)(**generate_kwargs)
            if isinstance(video_result, dict):
                video_data = video_result.get('data', [])
                metadata = video_result.get('metadata', {})
                success = video_result.get('success', True)
                error = video_result.get('error')
            else:
                video_data = [{'url': url} if isinstance(url, str) else url for url in video_result]
                metadata = {}
                success = True
                error = None

            ai_response = AIResponse(
                success=success,
                data=video_data,
                metadata={
                    **metadata,
                    'model': provider.model_name,
                    'duration': duration,
                    'fps': fps,
                    'aspect_ratio': aspect_ratio,
                },
                error=error,
            )
        else:
            raise ImportError(f'不支持的图生视频执行器: {executor_class_path}')

        success = ai_response.success
        data = ai_response.data or []
        metadata = ai_response.metadata or {}
        error = ai_response.error
        text = ai_response.text

        return {
            'success': success,
            'text': text or ('Image2Video test successful' if success else ''),
            'data': {
                'prompt': prompt,
                'provider': provider.name,
                'videos': data,
                'metadata': metadata,
                'test_image_url': image_url,
            },
            'tokens_used': metadata.get('usage', {}).get('total_tokens', 0),
            'error': error,
        }


    @staticmethod
    async def _test_image_edit_provider(
        provider: ModelProvider,
        prompt: str,
    ) -> Dict[str, Any]:
        """测试图片编辑提供商"""
        from core.ai_client.factory import create_ai_client

        extra_config = provider.extra_config or {}
        image_url = (
            extra_config.get('test_image_url')
            or extra_config.get('image_url')
            or extra_config.get('default_image_url')
            or 'mock'
        )
        width = extra_config.get('width', 1024)
        height = extra_config.get('height', 1024)
        strength = extra_config.get('strength', 0.35)
        mask_url = extra_config.get('mask_url', '')

        client = await sync_to_async(create_ai_client)(provider)
        ai_response = await sync_to_async(client.generate)(
            image_url=image_url,
            prompt=prompt,
            mask_url=mask_url,
            strength=strength,
            width=width,
            height=height,
        )

        return {
            'success': ai_response.success,
            'text': ai_response.text or ('ImageEdit test successful' if ai_response.success else ''),
            'data': {
                'prompt': prompt,
                'provider': provider.name,
                'images': ai_response.data,
                'metadata': ai_response.metadata,
                'test_image_url': image_url,
            },
            'tokens_used': ai_response.metadata.get('usage', {}).get('total_tokens', 0),
            'error': ai_response.error,
        }


class ModelUsageLogService:
    """
    模型使用日志服务
    职责: 处理使用日志相关业务逻辑
    """

    @staticmethod
    def get_logs_by_provider(
        provider_id: str,
        limit: int = 100
    ) -> List[ModelUsageLog]:
        """
        获取指定提供商的使用日志

        Args:
            provider_id: 提供商ID
            limit: 返回条数限制

        Returns:
            使用日志列表
        """
        return ModelUsageLog.objects.filter(
            model_provider_id=provider_id
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_logs_by_project(
        project_id: str,
        stage_type: Optional[str] = None
    ) -> List[ModelUsageLog]:
        """
        获取指定项目的使用日志

        Args:
            project_id: 项目ID
            stage_type: 阶段类型

        Returns:
            使用日志列表
        """
        queryset = ModelUsageLog.objects.filter(project_id=project_id)

        if stage_type:
            queryset = queryset.filter(stage_type=stage_type)

        return queryset.order_by('-created_at')

    @staticmethod
    def get_failed_logs(limit: int = 100) -> List[ModelUsageLog]:
        """
        获取失败的使用日志

        Args:
            limit: 返回条数限制

        Returns:
            失败日志列表
        """
        return ModelUsageLog.objects.filter(
            status='failed'
        ).order_by('-created_at')[:limit]

    @staticmethod
    def create_usage_log(data: Dict[str, Any]) -> ModelUsageLog:
        """
        创建使用日志

        Args:
            data: 日志数据

        Returns:
            创建的日志实例
        """
        return ModelUsageLog.objects.create(**data)
