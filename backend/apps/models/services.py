"""
模型管理服务层
职责: 处理模型提供商相关业务逻辑
遵循单一职责原则(SRP)和依赖倒置原则(DIP)
"""

import inspect
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.db.models import Q, Avg, Sum
from asgiref.sync import sync_to_async
from .models import ModelProvider, ModelUsageLog


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
