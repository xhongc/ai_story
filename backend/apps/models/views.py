"""
模型管理视图集
职责: 处理HTTP请求和业务逻辑编排
遵循单一职责原则(SRP)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync

from .models import ModelProvider, ModelUsageLog
from .serializers import (
    ModelProviderListSerializer,
    ModelProviderDetailSerializer,
    ModelProviderCreateSerializer,
    ModelProviderUpdateSerializer,
    ModelUsageLogSerializer,
    ModelProviderTestSerializer,
    ModelProviderSimpleSerializer,
    VendorModelDiscoverySerializer,
    VendorModelBatchCreateSerializer,
    VendorConnectionConfigSerializer,
    VendorConnectionConfigQuerySerializer,
)
from .services import ModelProviderService, ModelUsageLogService


class ModelProviderViewSet(viewsets.ModelViewSet):
    """
    模型提供商ViewSet

    提供模型提供商的CRUD操作和测试功能
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['provider_type', 'is_active']
    search_fields = ['name', 'model_name', 'api_url']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取所有模型提供商"""
        return ModelProvider.objects.all().prefetch_related('usage_logs')

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'list':
            return ModelProviderListSerializer
        elif self.action == 'retrieve':
            return ModelProviderDetailSerializer
        elif self.action == 'create':
            return ModelProviderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ModelProviderUpdateSerializer
        return ModelProviderDetailSerializer

    def create(self, request, *args, **kwargs):
        """创建模型提供商"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 使用服务层创建
        provider = ModelProviderService.create_provider(serializer.validated_data)

        # 返回详情
        response_serializer = ModelProviderDetailSerializer(provider)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """更新模型提供商"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # 使用服务层更新
        provider = ModelProviderService.update_provider(
            str(instance.id),
            serializer.validated_data
        )

        # 返回详情
        response_serializer = ModelProviderDetailSerializer(provider)
        return Response(response_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """删除模型提供商"""
        instance = self.get_object()

        # 检查是否被项目使用
        from apps.projects.models import ProjectModelConfig

        # 检查所有关联字段
        in_use = (
            ProjectModelConfig.objects.filter(rewrite_providers=instance).exists() or
            ProjectModelConfig.objects.filter(storyboard_providers=instance).exists() or
            ProjectModelConfig.objects.filter(image_providers=instance).exists() or
            ProjectModelConfig.objects.filter(camera_providers=instance).exists() or
            ProjectModelConfig.objects.filter(video_providers=instance).exists()
        )

        if in_use:
            return Response(
                {'error': '该模型提供商正在被项目使用,无法删除'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 使用服务层删除
        success = ModelProviderService.delete_provider(str(instance.id))

        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {'error': '删除失败'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        切换模型提供商激活状态
        POST /api/v1/models/providers/{id}/toggle-status/
        """
        instance = self.get_object()
        provider = ModelProviderService.toggle_provider_status(str(instance.id))

        return Response({
            'message': f'模型提供商已{"激活" if provider.is_active else "停用"}',
            'is_active': provider.is_active,
            'provider': ModelProviderDetailSerializer(provider).data
        })

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        获取模型提供商统计信息
        GET /api/v1/models/providers/{id}/statistics/
        """
        instance = self.get_object()
        stats = ModelProviderService.get_provider_statistics(str(instance.id))

        return Response(stats)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        测试模型提供商连接
        POST /api/v1/models/providers/{id}/test-connection/
        Body: {"test_prompt": "Hello, this is a test."}
        """
        instance = self.get_object()
        serializer = ModelProviderTestSerializer(
            data=request.data,
            context={'provider_id': str(instance.id)}
        )
        serializer.is_valid(raise_exception=True)

        test_prompt = serializer.validated_data.get(
            'test_prompt',
            'Hello, this is a test.'
        )
        test_image_url = serializer.validated_data.get('test_image_url', '')
        test_image_base64 = serializer.validated_data.get('test_image_base64', '')
        test_image_mime_type = serializer.validated_data.get('test_image_mime_type', 'image/jpeg')

        # 异步测试转同步执行
        result = async_to_sync(ModelProviderService.test_provider_connection)(
            str(instance.id),
            test_prompt,
            test_image_url=test_image_url,
            test_image_base64=test_image_base64,
            test_image_mime_type=test_image_mime_type,
        )

        if result['success']:
            return Response({
                'success': True,
                'message': '连接测试成功',
                'latency_ms': result['latency_ms'],
                'response': result.get('response'),
                'data': result.get('data', {})
            })
        else:
            return Response({
                'success': False,
                'message': '连接测试失败',
                'error': result.get('error'),
                'latency_ms': result.get('latency_ms', 0)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def usage_logs(self, request, pk=None):
        """
        获取模型提供商的使用日志
        GET /api/v1/models/providers/{id}/usage-logs/
        """
        instance = self.get_object()
        limit = int(request.query_params.get('limit', 100))

        logs = ModelUsageLogService.get_logs_by_provider(
            str(instance.id),
            limit=limit
        )

        serializer = ModelUsageLogSerializer(logs, many=True)
        return Response({
            'count': len(logs),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def active_providers(self, request):
        """
        获取所有激活的模型提供商
        GET /api/v1/models/providers/active-providers/
        Query: ?provider_type=llm
        """
        provider_type = request.query_params.get('provider_type')
        providers = ModelProviderService.get_active_providers(provider_type)

        serializer = ModelProviderListSerializer(providers, many=True)
        return Response({
            'count': len(providers),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        按类型分组获取模型提供商
        GET /api/v1/models/providers/by-type/
        """
        llm_providers = ModelProvider.objects.filter(
            provider_type='llm',
            is_active=True
        ).order_by('-priority')

        text2image_providers = ModelProvider.objects.filter(
            provider_type='text2image',
            is_active=True
        ).order_by('-priority')

        image2video_providers = ModelProvider.objects.filter(
            provider_type='image2video',
            is_active=True
        ).order_by('-priority')

        image_edit_providers = ModelProvider.objects.filter(
            provider_type='image_edit',
            is_active=True
        ).order_by('-priority')

        return Response({
            'llm': ModelProviderListSerializer(llm_providers, many=True).data,
            'text2image': ModelProviderListSerializer(text2image_providers, many=True).data,
            'image2video': ModelProviderListSerializer(image2video_providers, many=True).data,
            'image_edit': ModelProviderListSerializer(image_edit_providers, many=True).data,
        })

    @action(detail=False, methods=['get'])
    def simple_list(self, request):
        """
        获取简化的模型列表(仅id和name) - 用于下拉选择
        GET /api/v1/models/providers/simple-list/
        Query: ?provider_type=llm
        """
        provider_type = request.query_params.get('provider_type')

        queryset = ModelProvider.objects.filter(is_active=True)

        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)

        queryset = queryset.order_by('-priority', 'name')

        serializer = ModelProviderSimpleSerializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def executor_choices(self, request):
        """
        获取执行器选项列表
        GET /api/v1/models/providers/executor-choices/
        Query: ?provider_type=llm

        返回格式:
        {
            "llm": [
                {"value": "core.ai_client.openai_client.OpenAIClient", "label": "OpenAI兼容客户端"}
            ],
            "text2image": [...],
            "image2video": [...]
        }
        """
        provider_type = request.query_params.get('provider_type')

        # 如果指定了provider_type，只返回该类型的执行器
        if provider_type:
            temp_instance = ModelProvider(provider_type=provider_type)
            executor_choices = temp_instance.get_executor_choices()

            return Response({
                'provider_type': provider_type,
                'executors': [
                    {'value': choice[0], 'label': choice[1]}
                    for choice in executor_choices
                ]
            })

        # 否则返回所有类型的执行器
        all_executors = {}

        for ptype, _ in ModelProvider.PROVIDER_TYPES:
            temp_instance = ModelProvider(provider_type=ptype)
            executor_choices = temp_instance.get_executor_choices()

            all_executors[ptype] = [
                {'value': choice[0], 'label': choice[1]}
                for choice in executor_choices
            ]

        return Response(all_executors)

    @action(detail=False, methods=['get'])
    def builtin_vendors(self, request):
        """获取内置厂商目录。"""
        vendors = ModelProviderService.list_builtin_vendors()
        return Response({
            'count': len(vendors),
            'results': vendors,
        })

    @action(detail=False, methods=['get', 'put'])
    def vendor_connection_config(self, request):
        """获取或保存当前用户的厂商导入连接配置。"""
        if request.method.lower() == 'get':
            serializer = VendorConnectionConfigQuerySerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            config = ModelProviderService.get_vendor_connection_config(
                user=request.user,
                vendor=serializer.validated_data['vendor'],
                capability=serializer.validated_data['capability'],
            )
            if not config:
                return Response({
                    'vendor': serializer.validated_data['vendor'],
                    'capability': serializer.validated_data['capability'],
                    'api_key': '',
                    'api_url': '',
                })
            return Response(VendorConnectionConfigSerializer(config).data)

        serializer = VendorConnectionConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = ModelProviderService.save_vendor_connection_config(
            user=request.user,
            vendor=serializer.validated_data['vendor'],
            capability=serializer.validated_data['capability'],
            api_key=serializer.validated_data.get('api_key', ''),
            api_url=serializer.validated_data.get('api_url', ''),
        )
        return Response(VendorConnectionConfigSerializer(config).data)

    @action(detail=False, methods=['post'])
    def discover_vendor_models(self, request):
        """根据厂商和 API Key 拉取模型列表。"""
        serializer = VendorModelDiscoverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ModelProviderService.discover_vendor_models(
                vendor=serializer.validated_data['vendor'],
                capability=serializer.validated_data['capability'],
                api_key=serializer.validated_data['api_key'],
                api_url=serializer.validated_data.get('api_url'),
            )
        except ValueError as error:
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            return Response({'error': f'获取厂商模型失败: {error}'}, status=status.HTTP_400_BAD_REQUEST)

        ModelProviderService.save_vendor_connection_config(
            user=request.user,
            vendor=serializer.validated_data['vendor'],
            capability=serializer.validated_data['capability'],
            api_key=serializer.validated_data['api_key'],
            api_url=result.get('api_url', serializer.validated_data.get('api_url', '')),
        )

        return Response(result)

    @action(detail=False, methods=['post'])
    def batch_create_vendor_models(self, request):
        """批量创建厂商模型。"""
        serializer = VendorModelBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = ModelProviderService.batch_create_vendor_models(serializer.validated_data)

        ModelProviderService.save_vendor_connection_config(
            user=request.user,
            vendor=serializer.validated_data['vendor'],
            capability=serializer.validated_data['capability'],
            api_key=serializer.validated_data['api_key'],
            api_url=result.get('api_url', serializer.validated_data.get('api_url', '')),
        )

        return Response({
            'vendor': result['vendor'],
            'vendor_label': result['vendor_label'],
            'capability': result['capability'],
            'provider_type': result['provider_type'],
            'created_count': result['created_count'],
            'skipped_count': result['skipped_count'],
            'created': ModelProviderDetailSerializer(result['created'], many=True).data,
            'skipped': result['skipped'],
        }, status=status.HTTP_201_CREATED)


class ModelUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    模型使用日志ViewSet

    只读API,用于查询使用日志
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ModelUsageLogSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model_provider', 'status', 'project_id', 'stage_type']
    ordering = ['-created_at']

    def get_queryset(self):
        """获取所有使用日志"""
        return ModelUsageLog.objects.all().select_related('model_provider')

    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """
        按项目获取使用日志
        GET /api/v1/models/usage-logs/by-project/
        Query: ?project_id=xxx&stage_type=rewrite
        """
        project_id = request.query_params.get('project_id')
        if not project_id:
            return Response(
                {'error': '缺少project_id参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        stage_type = request.query_params.get('stage_type')
        logs = ModelUsageLogService.get_logs_by_project(project_id, stage_type)

        serializer = self.get_serializer(logs, many=True)
        return Response({
            'count': len(logs),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def failed_logs(self, request):
        """
        获取失败的使用日志
        GET /api/v1/models/usage-logs/failed-logs/
        """
        limit = int(request.query_params.get('limit', 100))
        logs = ModelUsageLogService.get_failed_logs(limit=limit)

        serializer = self.get_serializer(logs, many=True)
        return Response({
            'count': len(logs),
            'results': serializer.data
        })
