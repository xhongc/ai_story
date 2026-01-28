"""
项目管理视图集
职责: 处理HTTP请求和业务逻辑编排
遵循单一职责原则(SRP)
"""

import json

from celery.result import AsyncResult
from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Project, ProjectModelConfig, ProjectStage
from .serializers import (
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectModelConfigSerializer,
    ProjectStageSerializer,
    ProjectTemplateSerializer,
    ProjectUpdateSerializer,
    StageExecuteSerializer,
    StageRetrySerializer,
)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    项目管理ViewSet

    提供项目的CRUD操作和工作流控制
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "prompt_template_set"]
    search_fields = ["name", "description", "original_topic"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """只返回当前用户的项目"""
        return (
            Project.objects.filter(user=self.request.user)
            .select_related("user", "prompt_template_set")
            .prefetch_related("stages")
        )

    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == "list":
            return ProjectListSerializer
        elif self.action == "retrieve":
            return ProjectDetailSerializer
        elif self.action == "create":
            return ProjectCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ProjectUpdateSerializer
        return ProjectDetailSerializer

    def perform_create(self, serializer):
        """创建项目时自动设置当前用户"""
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        """删除项目前检查状态"""
        instance.delete()

    @action(detail=True, methods=["get"])
    def stages(self, request, pk=None):
        """
        获取项目的所有阶段（简化版）
        GET /api/v1/projects/{id}/stages/

        返回格式:
        - 只返回 rewrite 和 storyboard 两条记录
        - storyboard 的 domain_data 中整合了 image_generation、camera_movement、video_generation 数据
        - 数据按分镜场景分组，每个场景包含对应的图片、运镜、视频数据
        """
        project = self.get_object()

        # 获取 rewrite 和 storyboard 阶段
        rewrite_stage = project.stages.filter(stage_type='rewrite').first()
        storyboard_stage = project.stages.filter(stage_type='storyboard').first()

        # 获取其他阶段用于数据整合
        image_stage = project.stages.filter(stage_type='image_generation').first()
        camera_stage = project.stages.filter(stage_type='camera_movement').first()
        video_stage = project.stages.filter(stage_type='video_generation').first()

        result = []

        # 1. 添加 rewrite 阶段
        if rewrite_stage:
            rewrite_serializer = ProjectStageSerializer(rewrite_stage)
            result.append(rewrite_serializer.data)

        # 2. 添加 storyboard 阶段（整合其他阶段数据）
        if storyboard_stage:
            storyboard_serializer = ProjectStageSerializer(storyboard_stage)
            storyboard_data = storyboard_serializer.data

            # 整合其他阶段的数据到 domain_data 中
            if storyboard_data.get('domain_data'):
                storyboard_data['domain_data'] = self._integrate_stage_data(
                    project,
                    storyboard_data['domain_data'],
                    image_stage,
                    camera_stage,
                    video_stage
                )

            result.append(storyboard_data)

        return Response(result)

    def _integrate_stage_data(self, project, storyboard_domain_data, image_stage, camera_stage, video_stage):
        """
        将 image_generation、camera_movement、video_generation 数据整合到 storyboard 的 domain_data 中

        Args:
            project: 项目对象
            storyboard_domain_data: storyboard 的原始 domain_data
            image_stage: image_generation 阶段对象
            camera_stage: camera_movement 阶段对象
            video_stage: video_generation 阶段对象

        Returns:
            dict: 整合后的 domain_data
        """
        from apps.content.models import Storyboard, GeneratedImage, CameraMovement, GeneratedVideo

        # 获取所有分镜场景
        storyboards = storyboard_domain_data.get('storyboards', [])

        # 为每个分镜场景整合数据
        for sb_data in storyboards:
            storyboard_id = sb_data.get('id')

            # 初始化默认数据结构
            sb_data['image_generation'] = {
                'status': image_stage.status if image_stage else 'pending',
                'images': []
            }
            sb_data['camera_movement'] = {
                'status': camera_stage.status if camera_stage else 'pending',
                'data': None
            }
            sb_data['video_generation'] = {
                'status': video_stage.status if video_stage else 'pending',
                'videos': []
            }

            if not storyboard_id:
                continue

            try:
                # 1. 整合 image_generation 数据
                if image_stage:
                    images = GeneratedImage.objects.filter(
                        storyboard_id=storyboard_id
                    ).select_related('model_provider').order_by('-created_at')

                    sb_data['image_generation']['images'] = [
                        {
                            'id': str(img.id),
                            'image_url': img.image_url,
                            'thumbnail_url': img.thumbnail_url,
                            'width': img.width,
                            'height': img.height,
                            'file_size': img.file_size,
                            'status': img.status,
                            'status_display': img.get_status_display(),
                            'model_provider': {
                                'id': str(img.model_provider.id) if img.model_provider else None,
                                'name': img.model_provider.name if img.model_provider else None,
                                'model_name': img.model_provider.model_name if img.model_provider else None,
                            } if img.model_provider else None,
                            'generation_params': img.generation_params,
                            'retry_count': img.retry_count,
                            'created_at': img.created_at.isoformat() if img.created_at else None,
                        }
                        for img in images
                    ]

                # 2. 整合 camera_movement 数据
                if camera_stage:
                    try:
                        camera = CameraMovement.objects.select_related('model_provider').get(
                            storyboard_id=storyboard_id
                        )
                        sb_data['camera_movement']['data'] = {
                            'id': str(camera.id),
                            'movement_type': camera.movement_type,
                            'movement_type_display': camera.get_movement_type_display() if camera.movement_type else None,
                            'movement_params': camera.movement_params,
                            'model_provider': {
                                'id': str(camera.model_provider.id) if camera.model_provider else None,
                                'name': camera.model_provider.name if camera.model_provider else None,
                                'model_name': camera.model_provider.model_name if camera.model_provider else None,
                            } if camera.model_provider else None,
                            'prompt_used': camera.prompt_used,
                            'generation_metadata': camera.generation_metadata,
                            'created_at': camera.created_at.isoformat() if camera.created_at else None,
                            'updated_at': camera.updated_at.isoformat() if camera.updated_at else None,
                        }
                    except CameraMovement.DoesNotExist:
                        pass

                # 3. 整合 video_generation 数据
                if video_stage:
                    videos = GeneratedVideo.objects.filter(
                        storyboard_id=storyboard_id
                    ).select_related('model_provider', 'image', 'camera_movement').order_by('-created_at')

                    sb_data['video_generation']['videos'] = [
                        {
                            'id': str(video.id),
                            'video_url': video.video_url,
                            'thumbnail_url': video.thumbnail_url,
                            'duration': video.duration,
                            'width': video.width,
                            'height': video.height,
                            'fps': video.fps,
                            'file_size': video.file_size,
                            'status': video.status,
                            'status_display': video.get_status_display(),
                            'image_id': str(video.image.id) if video.image else None,
                            'camera_movement_id': str(video.camera_movement.id) if video.camera_movement else None,
                            'model_provider': {
                                'id': str(video.model_provider.id) if video.model_provider else None,
                                'name': video.model_provider.name if video.model_provider else None,
                                'model_name': video.model_provider.model_name if video.model_provider else None,
                            } if video.model_provider else None,
                            'generation_params': video.generation_params,
                            'retry_count': video.retry_count,
                            'created_at': video.created_at.isoformat() if video.created_at else None,
                        }
                        for video in videos
                    ]

            except Exception as e:
                # 记录错误但不中断处理
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"整合分镜 {storyboard_id} 的数据失败: {str(e)}", exc_info=True)

        return storyboard_domain_data

    @action(detail=True, methods=["post"])
    def execute_stage(self, request, pk=None):
        """
        执行指定阶段
        POST /api/v1/projects/projects/{id}/execute_stage/
        Body: {
            "stage_name": "rewrite",
            "input_data": {...},
            "use_streaming": false  // 可选，true=SSE流式(旧方式), false=Celery异步(默认)
        }

        模式1 (默认): Celery异步任务
        返回:
        {
            "task_id": "celery-task-id",
            "channel": "ai_story:project:xxx:stage:rewrite",
            "message": "任务已启动"
        }
        """
        project = self.get_object()
        serializer = StageExecuteSerializer(
            data=request.data, context={"project_id": str(project.id)}
        )
        serializer.is_valid(raise_exception=True)

        stage_name = serializer.validated_data["stage_name"]
        input_data = serializer.validated_data.get("input_data", {})

        # 获取阶段
        stage = get_object_or_404(ProjectStage, project=project, stage_type=stage_name)

        # 更新项目状态为处理中
        if project.status != "processing":
            project.status = "processing"
            project.save()
        # 模式2: Celery异步任务 (默认，推荐)
        return self._execute_stage_async(project, stage_name, input_data)

    def _execute_stage_async(self, project, stage_name, input_data):
        """
        使用Celery异步执行阶段 (推荐方式)
        """
        from apps.projects.tasks import (
            execute_image2video_stage,
            execute_llm_stage,
            execute_text2image_stage,
        )

        # 根据阶段类型启动对应的Celery任务
        if stage_name in ["rewrite", "storyboard", "camera_movement"]:
            # LLM类阶段
            print("execute_llm_stage", settings.CELERY_BROKER_URL, execute_llm_stage.app.conf.broker_url)
            task = execute_llm_stage.delay(
                project_id=str(project.id),
                stage_name=stage_name,
                input_data=input_data,
                user_id=self.request.user.id,
            )
        elif stage_name == "image_generation":
            # 文生图阶段
            storyboard_ids = input_data.get("storyboard_ids", None)
            task = execute_text2image_stage.delay(
                project_id=str(project.id),
                storyboard_ids=storyboard_ids,
                user_id=self.request.user.id,
            )
        elif stage_name == "video_generation":
            # 图生视频阶段
            storyboard_ids = input_data.get("storyboard_ids", None)
            task = execute_image2video_stage.delay(
                project_id=str(project.id),
                storyboard_ids=storyboard_ids,
                user_id=self.request.user.id,
            )
        else:
            return Response(
                {"error": f"未知阶段类型: {stage_name}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 构建Redis频道名称
        channel = f"ai_story:project:{project.id}:stage:{stage_name}"

        return Response(
            {
                "task_id": task.id,
                "channel": channel,
                "stage": stage_name,
                "message": f"阶段 {stage_name} 任务已启动",
                "project_id": str(project.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def task_status(self, request, pk=None):
        """
        获取Celery任务状态
        GET /api/v1/projects/{id}/task-status/?task_id=xxx

        返回:
        {
            "task_id": "xxx",
            "state": "PENDING|STARTED|SUCCESS|FAILURE|RETRY",
            "result": {...},
            "info": {...}
        }
        """
        project = self.get_object()
        task_id = request.query_params.get("task_id")

        if not task_id:
            return Response(
                {"error": "缺少task_id参数"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 获取Celery任务结果
        task_result = AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "state": task_result.state,
            "project_id": str(project.id),
        }

        if task_result.state == "PENDING":
            response_data["info"] = "任务等待执行"
        elif task_result.state == "STARTED":
            response_data["info"] = "任务正在执行"
        elif task_result.state == "SUCCESS":
            response_data["result"] = task_result.result
            response_data["info"] = "任务执行成功"
        elif task_result.state == "FAILURE":
            response_data["error"] = str(task_result.info)
            response_data["info"] = "任务执行失败"
        elif task_result.state == "RETRY":
            response_data["info"] = "任务正在重试"
        else:
            response_data["info"] = task_result.info

        return Response(response_data)

    @action(detail=True, methods=["post"])
    def retry_stage(self, request, pk=None):
        """
        重试失败的阶段
        POST /api/v1/projects/{id}/retry-stage/
        Body: {"stage_name": "rewrite"}
        """
        project = self.get_object()
        serializer = StageRetrySerializer(
            data=request.data, context={"project_id": str(project.id)}
        )
        serializer.is_valid(raise_exception=True)

        stage_name = serializer.validated_data["stage_name"]
        stage = get_object_or_404(ProjectStage, project=project, stage_type=stage_name)

        # 增加重试次数
        stage.retry_count += 1
        stage.status = "processing"
        stage.error_message = ""
        stage.started_at = timezone.now()
        stage.save()

        # TODO: 调用Celery任务
        # from apps.content.tasks import execute_project_stage
        # execute_project_stage.delay(str(project.id), stage_name)

        return Response(
            {
                "message": f"阶段 {stage.get_stage_type_display()} 开始重试 (第{stage.retry_count}次)",
                "stage": ProjectStageSerializer(stage).data,
            }
        )

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """
        暂停项目
        POST /api/v1/projects/{id}/pause/
        """
        project = self.get_object()

        if project.status != "processing":
            return Response(
                {"error": "只有处理中的项目才能暂停"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project.status = "paused"
        project.save()

        # TODO: 取消Celery任务

        return Response(
            {
                "message": "项目已暂停",
                "project": ProjectDetailSerializer(project).data,
            }
        )

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """
        恢复暂停的项目
        POST /api/v1/projects/{id}/resume/
        """
        project = self.get_object()

        if project.status != "paused":
            return Response(
                {"error": "只有暂停的项目才能恢复"}, status=status.HTTP_400_BAD_REQUEST
            )

        project.status = "processing"
        project.save()

        # TODO: 重新启动Pipeline (从当前阶段继续)

        return Response(
            {
                "message": "项目已恢复",
                "project": ProjectDetailSerializer(project).data,
            }
        )

    @action(detail=True, methods=["post"])
    def rollback_stage(self, request, pk=None):
        """
        回滚到指定阶段
        POST /api/v1/projects/{id}/rollback-stage/
        Body: {"stage_name": "rewrite"}
        """
        project = self.get_object()
        stage_name = request.data.get("stage_name")

        if not stage_name:
            return Response(
                {"error": "缺少阶段名称"}, status=status.HTTP_400_BAD_REQUEST
            )

        stage = get_object_or_404(ProjectStage, project=project, stage_type=stage_name)

        # 重置该阶段及后续阶段
        stage_order = [
            "rewrite",
            "storyboard",
            "image_generation",
            "camera_movement",
            "video_generation",
        ]
        current_index = stage_order.index(stage_name)

        # 重置当前及后续阶段
        for stage_type in stage_order[current_index:]:
            ProjectStage.objects.filter(project=project, stage_type=stage_type).update(
                status="pending",
                output_data={},
                error_message="",
                retry_count=0,
                started_at=None,
                completed_at=None,
            )

        # 更新项目状态
        project.status = "draft"
        project.save()

        return Response(
            {
                "message": f"已回滚到阶段 {stage.get_stage_type_display()}",
                "project": ProjectDetailSerializer(project).data,
            }
        )

    @action(detail=True, methods=["get"])
    def model_config(self, request, pk=None):
        """
        获取项目模型配置
        GET /api/v1/projects/{id}/model-config/
        """
        project = self.get_object()
        config, created = ProjectModelConfig.objects.get_or_create(project=project)
        serializer = ProjectModelConfigSerializer(config)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def update_model_config(self, request, pk=None):
        """
        更新项目模型配置
        PATCH /api/v1/projects/{id}/update-model-config/
        """
        project = self.get_object()
        config, created = ProjectModelConfig.objects.get_or_create(project=project)
        serializer = ProjectModelConfigSerializer(
            config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def save_as_template(self, request, pk=None):
        """
        将项目保存为模板
        POST /api/v1/projects/{id}/save-as-template/
        Body: {"template_name": "我的模板", "include_model_config": true}
        """
        project = self.get_object()
        serializer = ProjectTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template_name = serializer.validated_data["template_name"]
        include_model_config = serializer.validated_data["include_model_config"]

        # TODO: 实现模板保存逻辑
        # 1. 复制项目基本信息
        # 2. 复制提示词集配置
        # 3. 如果include_model_config=True,复制模型配置
        # 4. 保存为可复用模板

        return Response(
            {
                "message": f"项目已保存为模板: {template_name}",
                "template_name": template_name,
            }
        )

    @action(detail=True, methods=["post"])
    def export(self, request, pk=None):
        """
        导出项目(合成视频、生成字幕)
        POST /api/v1/projects/{id}/export/
        Body: {"include_subtitles": true, "video_format": "mp4"}
        """
        project = self.get_object()

        if project.status != "completed":
            return Response(
                {"error": "只有完成的项目才能导出"}, status=status.HTTP_400_BAD_REQUEST
            )

        include_subtitles = request.data.get("include_subtitles", True)
        video_format = request.data.get("video_format", "mp4")

        # TODO: 实现视频导出逻辑
        # 1. 获取所有生成的视频片段
        # 2. 按分镜顺序合成完整视频
        # 3. 如果include_subtitles=True,生成并嵌入字幕
        # 4. 返回下载链接

        return Response(
            {
                "message": "导出任务已创建",
                "export_id": "TODO",
                "status": "processing",
            }
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        获取项目统计信息
        GET /api/v1/projects/statistics/
        """
        user = request.user
        projects = Project.objects.filter(user=user)

        stats = {
            "total_projects": projects.count(),
            "draft_projects": projects.filter(status="draft").count(),
            "processing_projects": projects.filter(status="processing").count(),
            "completed_projects": projects.filter(status="completed").count(),
            "failed_projects": projects.filter(status="failed").count(),
            "paused_projects": projects.filter(status="paused").count(),
        }

        return Response(stats)

    @action(detail=True, methods=["patch"])
    def update_stage_data(self, request, pk=None):
        """
        更新指定阶段的输入/输出数据
        PATCH /api/v1/projects/{id}/update-stage-data/
        Body: {
            "stage_name": "rewrite",
            "input_data": {...},
            "output_data": {...}
        }
        """
        project = self.get_object()
        stage_name = request.data.get("stage_name")

        if not stage_name:
            return Response(
                {"error": "缺少阶段名称"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 获取阶段
        try:
            stage = ProjectStage.objects.get(project=project, stage_type=stage_name)
        except ProjectStage.DoesNotExist:
            return Response(
                {"error": f"阶段 {stage_name} 不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        # 更新输入数据(如果提供)
        if "input_data" in request.data:
            stage.input_data = request.data["input_data"]

        # 更新输出数据(如果提供)
        if "output_data" in request.data:
            stage.output_data = request.data["output_data"]

        stage.save()

        return Response(
            {
                "message": f"阶段 {stage.get_stage_type_display()} 数据已更新",
                "stage": ProjectStageSerializer(stage).data,
            }
        )

    @action(detail=True, methods=["post"])
    def generate_jianying_draft(self, request, pk=None):
        """
        生成剪映草稿
        POST /api/v1/projects/{id}/generate_jianying_draft/
        Body: {
            "background_music": "/path/to/music.mp3",  // 可选
            "draft_folder_path": "/path/to/drafts",    // 可选
            "music_volume": 0.6,                       // 可选，默认0.6
            "add_intro_animation": true,               // 可选，默认true
            "subtitle_size": 15,                       // 可选，默认15
            "width": 1080,                             // 可选，默认1080
            "height": 1920                             // 可选，默认1920（竖屏）
        }

        返回:
        {
            "task_id": "celery-task-id",
            "channel": "ai_story:project:xxx:jianying_draft",
            "message": "剪映草稿生成任务已启动"
        }
        """
        from apps.projects.tasks import generate_jianying_draft

        project = self.get_object()

        # 检查视频生成阶段是否完成
        video_stage = ProjectStage.objects.filter(
            project=project, stage_type="video_generation", status="completed"
        ).first()

        if not video_stage:
            return Response(
                {"error": "视频生成阶段未完成，无法生成剪映草稿"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 获取可选参数
        background_music = request.data.get("background_music")
        options = {
            "draft_folder_path": request.data.get("draft_folder_path"),
            "music_volume": request.data.get("music_volume", 0.6),
            "add_intro_animation": request.data.get("add_intro_animation", True),
            "subtitle_size": request.data.get("subtitle_size", 15),
            "width": request.data.get("width", 1080),
            "height": request.data.get("height", 1920),
        }

        # 过滤掉None值
        options = {k: v for k, v in options.items() if v is not None}

        # 启动Celery任务
        task = generate_jianying_draft.delay(
            project_id=str(project.id),
            user_id=self.request.user.id,
            background_music=background_music,
            **options
        )

        # 构建Redis频道名称
        channel = f"ai_story:project:{project.id}:jianying_draft"

        return Response(
            {
                "task_id": task.id,
                "channel": channel,
                "draft_path": task.result.get("draft_path", "todo"),
            },
            status=status.HTTP_200_OK,
        )


class ProjectStageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    项目阶段ViewSet

    只读API,用于查询阶段信息
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProjectStageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["stage_type", "status", "project"]
    ordering = ["created_at"]

    def get_queryset(self):
        """只返回当前用户项目的阶段"""
        return ProjectStage.objects.filter(
            project__user=self.request.user
        ).select_related("project")


class ProjectModelConfigViewSet(viewsets.ModelViewSet):
    """
    项目模型配置ViewSet
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProjectModelConfigSerializer

    def get_queryset(self):
        """只返回当前用户项目的配置"""
        return (
            ProjectModelConfig.objects.filter(project__user=self.request.user)
            .select_related("project")
            .prefetch_related(
                "rewrite_providers",
                "storyboard_providers",
                "image_providers",
                "camera_providers",
                "video_providers",
            )
        )
