"""
提示词管理视图
遵循单一职责原则(SRP): 每个ViewSet只负责一个模型的CRUD
遵循依赖倒置原则(DIP): 依赖抽象(序列化器)而非具体实现
"""

import asyncio
import json
import uuid
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from django.db.models import Q
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from jinja2 import Template
from rest_framework import status, viewsets, renderers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import StreamingHttpResponse

from apps.models.models import ModelProvider
from core.ai_client.factory import create_ai_client
from core.utils.file_storage import image_storage
from .models import (
    PromptTemplate,
    PromptTemplateSet,
    GlobalVariable,
    PromptDebugSession,
    PromptDebugRun,
    PromptDebugArtifact,
)
from .serializers import (
    PromptTemplateEvaluationSerializer,
    PromptTemplateListSerializer,
    PromptTemplatePreviewSerializer,
    PromptTemplateSerializer,
    PromptTemplateSetListSerializer,
    PromptTemplateSetSerializer,
    PromptTemplateValidateSerializer,
    GlobalVariableSerializer,
    GlobalVariableListSerializer,
    GlobalVariableBatchSerializer,
    PromptDebugSessionSerializer,
    PromptDebugRunSerializer,
    PromptDebugArtifactSerializer,
    PromptDebugRunCreateSerializer,
    PromptDebugSaveTemplateSerializer,
)
from .services import PromptEvaluationService
from .debug_services import PromptDebugService
from .client_param_specs import STAGE_CLIENT_PARAM_SPECS

class ServerSentEventRenderer(renderers.BaseRenderer):
    media_type = 'text/event-stream'
    format = 'event-stream'
    charset = 'utf-8'
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data



class PromptTemplateSetViewSet(viewsets.ModelViewSet):
    """
    提示词集ViewSet
    职责: 提示词集的CRUD和特殊操作
    """

    queryset = PromptTemplateSet.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_default', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return PromptTemplateSetListSerializer
        return PromptTemplateSetSerializer

    def get_queryset(self):
        """
        过滤查询集
        非管理员只能看到自己创建的或默认的提示词集
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(
                Q(created_by=user) | Q(is_default=True)
            )

        return queryset.prefetch_related('templates', 'created_by')

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        克隆提示词集
        POST /api/v1/prompts/sets/{id}/clone/
        Body: {"name": "新提示词集名称"}
        """
        original_set = self.get_object()
        new_name = request.data.get('name')

        if not new_name:
            return Response(
                {'error': '请提供新提示词集的名称'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建新提示词集
        new_set = PromptTemplateSet.objects.create(
            name=new_name,
            description=f'克隆自: {original_set.name}',
            is_active=True,
            is_default=False,
            created_by=request.user
        )

        # 复制所有模板
        for template in original_set.templates.all():
            PromptTemplate.objects.create(
                template_set=new_set,
                stage_type=template.stage_type,
                model_provider=template.model_provider,
                template_content=template.template_content,
                variables=template.variables,
                client_params=template.client_params,
                version=1,
                is_active=True
            )

        serializer = self.get_serializer(new_set)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        设置为默认提示词集
        POST /api/v1/prompts/sets/{id}/set_default/
        需要管理员权限
        """
        if not request.user.is_staff:
            return Response(
                {'error': '只有管理员可以设置默认提示词集'},
                status=status.HTTP_403_FORBIDDEN
            )

        prompt_set = self.get_object()

        # 取消其他默认提示词集
        PromptTemplateSet.objects.filter(is_default=True).update(is_default=False)

        # 设置当前为默认
        prompt_set.is_default = True
        prompt_set.save()

        serializer = self.get_serializer(prompt_set)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """
        获取默认提示词集
        GET /api/v1/prompts/sets/default/
        """
        default_set = PromptTemplateSet.objects.filter(is_default=True).first()

        if not default_set:
            return Response(
                {'error': '未设置默认提示词集'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(default_set)
        return Response(serializer.data)


class PromptTemplateViewSet(viewsets.ModelViewSet):
    """
    提示词模板ViewSet
    职责: 提示词模板的CRUD和特殊操作
    """

    queryset = PromptTemplate.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template_set', 'stage_type', 'is_active']
    search_fields = ['template_content']
    ordering_fields = ['created_at', 'updated_at', 'version']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return PromptTemplateListSerializer
        return PromptTemplateSerializer

    def get_queryset(self):
        """
        过滤查询集
        非管理员只能看到自己创建的提示词集的模板
        """
        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(
                Q(template_set__created_by=user) |
                Q(template_set__is_default=True)
            )

        return queryset.select_related('template_set', 'model_provider')

    def perform_create(self, serializer):
        """
        创建提示词模板时，检查是否已存在相同 template_set + stage_type 的模板
        如果存在，删除旧模板或提示用户更新
        """
        template_set = serializer.validated_data.get('template_set')
        stage_type = serializer.validated_data.get('stage_type')

        # 检查是否存在相同的模板
        existing_template = PromptTemplate.objects.filter(
            template_set=template_set,
            stage_type=stage_type
        ).first()

        if existing_template:
            # 验证权限
            if existing_template.template_set.created_by != self.request.user and not self.request.user.is_staff:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('无权限修改此模板')

            # 删除旧模板（可选：改为更新旧模板）
            existing_template.delete()

        serializer.save()

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        创建新版本
        POST /api/v1/prompts/templates/{id}/create_version/
        Body: {
            "template_content": "新模板内容",
            "variables": {"topic": "string"}
        }
        """
        original_template = self.get_object()

        # 验证权限
        if original_template.template_set.created_by != request.user and not request.user.is_staff:
            return Response(
                {'error': '无权限修改此模板'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 创建新版本
        serializer = PromptTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_template = PromptTemplate.objects.create(
            template_set=original_template.template_set,
            stage_type=original_template.stage_type,
            model_provider=serializer.validated_data.get('model_provider', original_template.model_provider),
            template_content=serializer.validated_data['template_content'],
            variables=serializer.validated_data.get('variables', {}),
            client_params=serializer.validated_data.get('client_params', {}),
            version=original_template.version + 1,
            is_active=True
        )

        # 停用旧版本
        original_template.is_active = False
        original_template.save()

        response_serializer = PromptTemplateSerializer(new_template)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        获取版本历史
        GET /api/v1/prompts/templates/{id}/versions/

        注意: 当前实现返回同一stage_type的所有版本
        完整的版本控制需要使用django-simple-history
        """
        template = self.get_object()

        # 获取���一阶段类型的所有版本
        versions = PromptTemplate.objects.filter(
            template_set=template.template_set,
            stage_type=template.stage_type
        ).order_by('-version')

        serializer = PromptTemplateSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """
        验证模板语法
        POST /api/v1/prompts/templates/{id}/validate/
        Body: {"template_content": "要验证的模板内容"}
        """
        serializer = PromptTemplateValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            'valid': True,
            'message': '模板语法正确'
        })

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        预览模板渲染结果
        POST /api/v1/prompts/templates/{id}/preview/
        Body: {
            "variables": {
                "topic": "科幻故事",
                "style": "赛博朋克"
            }
        }
        """
        template = self.get_object()
        serializer = PromptTemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variables = serializer.validated_data['variables']

        try:
            # 渲染模板
            jinja_template = Template(template.template_content)
            rendered = jinja_template.render(**variables)

            return Response({
                'success': True,
                'rendered_content': rendered,
                'variables_used': variables
            })
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'渲染失败: {str(e)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        """
        AI评估提示词效果
        POST /api/v1/prompts/templates/{id}/evaluate/

        使用AI分析提示词质量,提供优化建议
        """
        template = self.get_object()

        try:
            # 使用评估服务进行AI分析
            evaluation_service = PromptEvaluationService()
            evaluation_result = asyncio.run(
                evaluation_service.evaluate_prompt(template)
            )

            serializer = PromptTemplateEvaluationSerializer(data=evaluation_result)
            serializer.is_valid(raise_exception=True)

            return Response(serializer.data)
        except Exception as e:
            return Response(
                {
                    'error': f'评估失败: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def client_param_schema(self, request):
        stage_type = request.query_params.get('stage_type', '').strip()
        if stage_type:
            return Response({
                'stage_type': stage_type,
                'schema': STAGE_CLIENT_PARAM_SPECS.get(stage_type, []),
            })

        return Response({
            'schema': STAGE_CLIENT_PARAM_SPECS,
        })


class GlobalVariableViewSet(viewsets.ModelViewSet):
    """
    全局变量ViewSet
    职责: 全局变量的CRUD和特殊操作
    """

    queryset = GlobalVariable.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scope', 'group', 'variable_type', 'is_active', 'created_by']
    search_fields = ['key', 'description', 'group']
    ordering_fields = ['created_at', 'updated_at', 'key', 'group']
    ordering = ['group', 'key']

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return GlobalVariableListSerializer
        elif self.action == 'batch_create':
            return GlobalVariableBatchSerializer
        return GlobalVariableSerializer

    def get_queryset(self):
        """
        过滤查询集
        用户可以看到:
        1. 自己创建的用户级变量
        2. 所有系统级变量
        """
        queryset = super().get_queryset()
        user = self.request.user

        # 用户可以看到自己的用户级变量 + 所有系统级变量
        queryset = queryset.filter(
            Q(created_by=user, scope='user') |
            Q(scope='system')
        )

        return queryset.select_related('created_by')

    def perform_destroy(self, instance):
        """
        删除变量时的权限检查
        系统级变量只能由管理员删除
        """
        if instance.scope == 'system' and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只有管理员可以删除系统级变量')

        super().perform_destroy(instance)

    def _get_default_image_provider(self):
        return ModelProvider.objects.filter(provider_type='text2image', is_active=True).first()

    def _get_requested_image_provider(self, provider_id):
        if provider_id:
            return ModelProvider.objects.filter(
                id=provider_id,
                provider_type='text2image',
                is_active=True,
            ).first()
        return self._get_default_image_provider()

    def _build_image_asset_file(self, image_url):
        if not image_url:
            raise ValueError('缺少图片地址')

        if image_url.startswith('/api/v1/content/storage/image/'):
            relative_path = image_url.split('/api/v1/content/storage/image/', 1)[1]
            file_path = image_storage.base_dir / relative_path
            if not file_path.exists():
                raise ValueError('生成图片不存在，无法保存为资产')
            return ContentFile(file_path.read_bytes(), name=Path(relative_path).name)

        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        filename = Path(image_url.split('?', 1)[0]).name or f'{uuid.uuid4().hex}.png'
        return ContentFile(response.content, name=filename)

    @action(detail=False, methods=['get'])
    def groups(self, request):
        """
        获取所有变量分组
        GET /api/v1/prompts/variables/groups/
        """
        queryset = self.get_queryset()
        groups = queryset.values_list('group', flat=True).distinct()
        groups = [g for g in groups if g]  # 过滤空字符串

        return Response({
            'groups': sorted(groups)
        })

    @action(detail=False, methods=['get'])
    async def for_template(self, request):
        """
        获取可用于模板渲染的变量字典
        GET /api/v1/prompts/variables/for_template/
        Query params:
            - include_system: 是否包含系统级变量 (默认: true)

        返回格式: {key: typed_value}
        """
        include_system = request.query_params.get('include_system', 'true').lower() == 'true'

        variables = await GlobalVariable.get_variables_for_user(
            user=request.user,
            include_system=include_system
        )

        return Response({
            'variables': variables,
            'count': len(variables)
        })

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """
        批量创建/更新变量
        POST /api/v1/prompts/variables/batch_create/
        Body: {
            "variables": [
                {
                    "key": "brand_name",
                    "value": "我的品牌",
                    "variable_type": "string",
                    "scope": "user",
                    "group": "品牌信息",
                    "description": "品牌名称"
                },
                ...
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variables_data = serializer.validated_data['variables']
        created = []
        updated = []
        errors = []

        for var_data in variables_data:
            key = var_data.get('key')
            scope = var_data.get('scope', 'user')

            # 检查是否已存在
            existing = GlobalVariable.objects.filter(
                key=key,
                created_by=request.user,
                scope=scope
            ).first()

            try:
                if existing:
                    # 更新现有变量
                    var_serializer = GlobalVariableSerializer(
                        existing,
                        data=var_data,
                        context={'request': request},
                        partial=True
                    )
                    var_serializer.is_valid(raise_exception=True)
                    var_serializer.save()
                    updated.append(var_serializer.data)
                else:
                    # 创建新变量
                    var_serializer = GlobalVariableSerializer(
                        data=var_data,
                        context={'request': request}
                    )
                    var_serializer.is_valid(raise_exception=True)
                    var_serializer.save()
                    created.append(var_serializer.data)
            except Exception as e:
                errors.append({
                    'key': key,
                    'error': str(e)
                })

        return Response({
            'created': created,
            'updated': updated,
            'errors': errors,
            'summary': {
                'created_count': len(created),
                'updated_count': len(updated),
                'error_count': len(errors)
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def validate_key(self, request):
        """
        验证变量键是否可用
        POST /api/v1/prompts/variables/validate_key/
        Body: {
            "key": "my_variable",
            "scope": "user"
        }
        """
        key = request.data.get('key')
        scope = request.data.get('scope', 'user')

        if not key:
            return Response(
                {'error': '请提供变量键'},
                status=status.HTTP_400_BAD_REQUEST
            )

        key = str(key).strip()
        if not key:
            return Response({
                'valid': False,
                'message': '变量键不能为空'
            })

        # 检查是否已存在
        exists = GlobalVariable.objects.filter(
            key=key,
            created_by=request.user,
            scope=scope
        ).exists()

        if exists:
            return Response({
                'valid': False,
                'message': f'变量键 "{key}" 在当前作用域下已存在'
            })

        return Response({
            'valid': True,
            'message': '变量键可用'
        })

    @action(detail=False, methods=['post'])
    def generate_image(self, request):
        prompt = str(request.data.get('prompt') or '').strip()
        provider_id = request.data.get('provider_id')
        if not prompt:
            return Response({'error': '缺少生成提示词'}, status=status.HTTP_400_BAD_REQUEST)

        provider = self._get_requested_image_provider(provider_id)
        if not provider:
            return Response({'error': '未配置可用的文生图模型'}, status=status.HTTP_400_BAD_REQUEST)

        extra_config = provider.extra_config or {}
        width = int(request.data.get('width') or extra_config.get('width') or 1024)
        height = int(request.data.get('height') or extra_config.get('height') or 1024)
        ratio = request.data.get('ratio') or extra_config.get('ratio') or '1:1'
        resolution = request.data.get('resolution') or extra_config.get('resolution') or '2k'

        client = create_ai_client(provider)
        response = client.generate(
            api_url=provider.api_url,
            session_id=provider.api_key,
            model=provider.model_name,
            prompt=prompt,
            ratio=ratio,
            resolution=resolution,
            width=width,
            height=height,
        )

        images = response.data if hasattr(response, 'data') else None
        if isinstance(images, dict):
            images = [images]
        if not response or not getattr(response, 'success', False) or not isinstance(images, list) or not images:
            return Response(
                {'error': getattr(response, 'error', None) or '文生图生成失败'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preview = dict(images[0])
        preview['prompt'] = prompt
        preview['provider'] = {
            'id': str(provider.id),
            'name': provider.name,
            'model_name': provider.model_name,
        }

        return Response({
            'message': '图片预览已生成',
            'preview': preview,
        })

    @action(detail=False, methods=['post'])
    def create_image_asset(self, request):
        asset_id = request.data.get('asset_id')
        key = str(request.data.get('key') or '').strip()
        prompt = str(request.data.get('prompt') or request.data.get('value') or '').strip()
        preview_url = str(request.data.get('preview_url') or '').strip()
        scope = request.data.get('scope') or 'user'

        if not key:
            return Response({'error': '资产键不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not preview_url:
            return Response({'error': '缺少生成图片预览地址'}, status=status.HTTP_400_BAD_REQUEST)
        if scope == 'system' and not request.user.is_staff:
            return Response({'error': '只有管理员可以创建系统级变量'}, status=status.HTTP_403_FORBIDDEN)

        asset = None
        if asset_id:
            asset = self.get_queryset().filter(pk=asset_id).first()
            if not asset:
                return Response({'error': '资产不存在或无权限访问'}, status=status.HTTP_404_NOT_FOUND)
            if asset.scope == 'system' and not request.user.is_staff:
                return Response({'error': '只有管理员可以修改系统级变量'}, status=status.HTTP_403_FORBIDDEN)

        owner = asset.created_by if asset else request.user
        queryset = GlobalVariable.objects.filter(
            key=key,
            created_by=owner,
            scope=scope,
        )
        if asset:
            queryset = queryset.exclude(pk=asset.pk)
        if queryset.exists():
            return Response({'error': f'变量键 "{key}" 在当前作用域下已存在'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image_file = self._build_image_asset_file(preview_url)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if asset is None:
            asset = GlobalVariable(created_by=request.user)

        asset.key = key
        asset.value = prompt
        asset.variable_type = 'image'
        asset.scope = scope
        asset.group = str(request.data.get('group') or '').strip()
        asset.description = str(request.data.get('description') or '').strip()
        asset.is_active = str(request.data.get('is_active', 'true')).lower() not in ('false', '0', 'off', 'no')
        asset.image_file.save(image_file.name, image_file, save=False)
        asset.save()

        serializer = GlobalVariableSerializer(asset, context={'request': request})
        return Response({
            'message': '图片资产保存成功',
            'asset': serializer.data,
        }, status=status.HTTP_200_OK if asset_id else status.HTTP_201_CREATED)


class PromptDebugSessionViewSet(viewsets.ModelViewSet):
    """提示词调试会话视图集"""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stage_type', 'template_set', 'prompt_template']
    ordering = ['-updated_at']

    def get_queryset(self):
        return PromptDebugSession.objects.filter(
            created_by=self.request.user
        ).select_related(
            'prompt_template', 'template_set', 'model_provider', 'latest_source_artifact'
        ).prefetch_related('runs__artifacts')

    def get_serializer_class(self):
        return PromptDebugSessionSerializer

    def perform_create(self, serializer):
        prompt_template = serializer.validated_data['prompt_template']
        serializer.save(
            created_by=self.request.user,
            template_set=prompt_template.template_set,
            stage_type=prompt_template.stage_type,
            draft_template_content=serializer.validated_data.get('draft_template_content') or prompt_template.template_content,
            draft_variables=serializer.validated_data.get('draft_variables') or prompt_template.variables,
        )

    @action(detail=False, methods=['post'])
    def bootstrap(self, request):
        template_id = request.data.get('prompt_template_id')
        if not template_id:
            return Response({'error': '缺少 prompt_template_id'}, status=status.HTTP_400_BAD_REQUEST)

        template = PromptTemplate.objects.filter(
            Q(id=template_id),
            Q(template_set__created_by=request.user) | Q(template_set__is_default=True)
        ).first()
        if not template:
            return Response({'error': '模板不存在或无权限访问'}, status=status.HTTP_404_NOT_FOUND)

        session = PromptDebugService.get_or_create_session(template, request.user)
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        session = self.get_object()
        serializer = PromptDebugRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        template_content = validated.get('template_content') or session.draft_template_content or session.prompt_template.template_content

        try:
            run = PromptDebugService.run_session(
                session=session,
                user=request.user,
                template_content=template_content,
                variable_values=validated.get('variable_values') or {},
                input_payload=validated.get('input_payload') or {},
                source_artifact_id=validated.get('source_artifact_id'),
                provider_id=validated.get('model_provider_id'),
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PromptDebugRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='run-stream-init')
    def run_stream_init(self, request, pk=None):
        session = self.get_object()
        if session.stage_type not in ('rewrite', 'asset_extraction', 'storyboard', 'camera_movement'):
            return Response({'error': '仅 LLM 类型阶段支持流式调试'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PromptDebugRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        template_content = validated.get('template_content') or session.draft_template_content or session.prompt_template.template_content

        stream_token = uuid.uuid4().hex
        cache.set(
            f'prompt_debug_stream:{stream_token}',
            {
                'session_id': str(session.id),
                'user_id': request.user.id,
                'template_content': template_content,
                'variable_values': validated.get('variable_values') or {},
                'input_payload': validated.get('input_payload') or {},
                'source_artifact_id': str(validated.get('source_artifact_id') or ''),
                'provider_id': str(validated.get('model_provider_id') or ''),
            },
            timeout=300,
        )

        return Response({'stream_token': stream_token})

    @action(detail=True, methods=['get'], url_path='run-stream', permission_classes=[AllowAny], renderer_classes=[ServerSentEventRenderer])
    def run_stream(self, request, pk=None):
        session = PromptDebugSession.objects.select_related('created_by', 'prompt_template').filter(id=pk).first()
        if not session:
            return Response({'error': '调试会话不存在'}, status=status.HTTP_404_NOT_FOUND)
        if session.stage_type not in ('rewrite', 'asset_extraction', 'storyboard', 'camera_movement'):
            return Response({'error': '仅 LLM 类型阶段支持流式调试'}, status=status.HTTP_400_BAD_REQUEST)

        stream_token = request.query_params.get('stream_token', '').strip()
        if not stream_token:
            return Response({'error': '缺少 stream_token'}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f'prompt_debug_stream:{stream_token}'
        stream_payload = cache.get(cache_key)
        if not stream_payload:
            return Response({'error': '流式调试令牌无效或已过期'}, status=status.HTTP_404_NOT_FOUND)

        if stream_payload.get('session_id') != str(session.id):
            return Response({'error': '流式调试令牌不匹配'}, status=status.HTTP_400_BAD_REQUEST)

        if stream_payload.get('user_id') != session.created_by_id:
            return Response({'error': '流式调试令牌无权限'}, status=status.HTTP_403_FORBIDDEN)

        def event_stream():
            try:
                for event in PromptDebugService.stream_llm_session(
                    session=session,
                    user=session.created_by,
                    template_content=stream_payload.get('template_content') or session.prompt_template.template_content,
                    variable_values=stream_payload.get('variable_values') or {},
                    input_payload=stream_payload.get('input_payload') or {},
                    source_artifact_id=stream_payload.get('source_artifact_id') or None,
                    provider_id=stream_payload.get('provider_id') or None,
                ):
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f'data: {payload}\n\n'
            except Exception as exc:
                payload = json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)
                yield f'data: {payload}\n\n'
            finally:
                cache.delete(cache_key)

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream; charset=utf-8')
        response['Cache-Control'] = 'no-cache, no-transform'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'
        return response

    @action(detail=True, methods=['post'])
    def save_template(self, request, pk=None):
        session = self.get_object()
        serializer = PromptDebugSaveTemplateSerializer(data=request.data, context={'session': session})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            template = PromptDebugService.save_to_template(
                session=session,
                template_content=validated['template_content'],
                variables=validated.get('variables') or {},
                client_params=validated.get('client_params') or {},
                model_provider_id=validated.get('model_provider_id'),
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PromptTemplateSerializer(template).data)

    @action(detail=True, methods=['post'])
    def save_as_version(self, request, pk=None):
        session = self.get_object()
        serializer = PromptDebugSaveTemplateSerializer(data=request.data, context={'session': session})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            template = PromptDebugService.create_template_version(
                session=session,
                template_content=validated['template_content'],
                variables=validated.get('variables') or {},
                client_params=validated.get('client_params') or {},
                model_provider_id=validated.get('model_provider_id'),
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PromptTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


class PromptDebugRunViewSet(viewsets.ReadOnlyModelViewSet):
    """提示词调试运行只读视图集"""

    permission_classes = [IsAuthenticated]
    serializer_class = PromptDebugRunSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session', 'stage_type', 'status', 'model_provider']
    ordering = ['-created_at']

    def get_queryset(self):
        return PromptDebugRun.objects.filter(
            session__created_by=self.request.user
        ).select_related('session', 'model_provider', 'source_artifact').prefetch_related('artifacts')


class PromptDebugArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    """提示词调试资产只读视图集"""

    permission_classes = [IsAuthenticated]
    serializer_class = PromptDebugArtifactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['run', 'artifact_type', 'stage_type', 'source_artifact']
    ordering = ['stage_type', 'sequence_number', '-created_at']

    def get_queryset(self):
        queryset = PromptDebugArtifact.objects.filter(created_by=self.request.user).select_related(
            'run', 'source_artifact'
        )
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(run__session_id=session_id)
        return queryset
