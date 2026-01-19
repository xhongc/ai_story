"""
项目管理序列化器
职责: 数据序列化与验证
遵循单一职责原则(SRP)
"""

from rest_framework import serializers

from apps.projects.utils import parse_storyboard_json
from .models import Project, ProjectStage, ProjectModelConfig


class ProjectStageSerializer(serializers.ModelSerializer):
    """项目阶段序列化器 - 返回真实的领域模型数据"""

    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # 添加领域模型数据字段
    domain_data = serializers.SerializerMethodField()

    class Meta:
        model = ProjectStage
        fields = [
            'id', 'project', 'stage_type', 'stage_type_display',
            'status', 'status_display', 'input_data', 'output_data',
            'retry_count', 'max_retries', 'error_message',
            'started_at', 'completed_at', 'created_at',
            'domain_data'  # 新增字段
        ]
        read_only_fields = ['id', 'created_at', 'started_at', 'completed_at']

    def get_domain_data(self, instance):
        """
        根据阶段类型返回对应的领域模型数据

        Returns:
            dict: 包含领域模型数据的字典
        """
        from apps.content.models import ContentRewrite, Storyboard, GeneratedImage, CameraMovement

        stage_type = instance.stage_type
        project = instance.project

        try:
            if stage_type == 'rewrite':
                # 返回文案改写数据
                try:
                    rewrite = ContentRewrite.objects.select_related('model_provider').get(project=project)
                    return {
                        'id': str(rewrite.id),
                        'original_text': rewrite.original_text,
                        'rewritten_text': rewrite.rewritten_text,
                        'model_provider': {
                            'id': str(rewrite.model_provider.id) if rewrite.model_provider else None,
                            'name': rewrite.model_provider.name if rewrite.model_provider else None,
                            'model_name': rewrite.model_provider.model_name if rewrite.model_provider else None,
                        } if rewrite.model_provider else None,
                        'prompt_used': rewrite.prompt_used,
                        'generation_metadata': rewrite.generation_metadata,
                        'created_at': rewrite.created_at.isoformat() if rewrite.created_at else None,
                        'updated_at': rewrite.updated_at.isoformat() if rewrite.updated_at else None,
                    }
                except ContentRewrite.DoesNotExist:
                    return None

            elif stage_type == 'storyboard':
                # 返回分镜列表数据
                storyboards = Storyboard.objects.filter(
                    project=project
                ).select_related('model_provider').order_by('sequence_number')

                return {
                    'count': storyboards.count(),
                    'storyboards': [
                        {
                            'id': str(sb.id),
                            'sequence_number': sb.sequence_number,
                            'scene_description': sb.scene_description,
                            'narration_text': sb.narration_text,
                            'image_prompt': sb.image_prompt,
                            'duration_seconds': sb.duration_seconds,
                            'model_provider': {
                                'id': str(sb.model_provider.id) if sb.model_provider else None,
                                'name': sb.model_provider.name if sb.model_provider else None,
                                'model_name': sb.model_provider.model_name if sb.model_provider else None,
                            } if sb.model_provider else None,
                            'prompt_used': sb.prompt_used,
                            'generation_metadata': sb.generation_metadata,
                            'created_at': sb.created_at.isoformat() if sb.created_at else None,
                            'updated_at': sb.updated_at.isoformat() if sb.updated_at else None,
                        }
                        for sb in storyboards
                    ]
                }

            elif stage_type == 'image_generation':
                # 返回生成的图片数据
                storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')

                result = []
                for sb in storyboards:
                    images = GeneratedImage.objects.filter(
                        storyboard=sb
                    ).select_related('model_provider').order_by('-created_at')

                    result.append({
                        'storyboard_id': str(sb.id),
                        'sequence_number': sb.sequence_number,
                        'images': [
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
                    })

                return {
                    'count': len(result),
                    'storyboards': result
                }

            elif stage_type == 'camera_movement':
                # 返回运镜数据
                storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')

                result = []
                for sb in storyboards:
                    try:
                        camera = CameraMovement.objects.select_related('model_provider').get(storyboard=sb)
                        result.append({
                            'storyboard_id': str(sb.id),
                            'sequence_number': sb.sequence_number,
                            'camera_movement': {
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
                        })
                    except CameraMovement.DoesNotExist:
                        result.append({
                            'storyboard_id': str(sb.id),
                            'sequence_number': sb.sequence_number,
                            'camera_movement': None
                        })

                return {
                    'count': len(result),
                    'storyboards': result
                }

            elif stage_type == 'video_generation':
                # 返回生成的视频数据
                # TODO: 实现视频数据序列化
                return None

            else:
                return None

        except Exception as e:
            # 记录错误但不中断序列化
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"获取阶段 {stage_type} 的领域数据失败: {str(e)}", exc_info=True)
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        stage_type = data.get("stage_type")
        if stage_type == "storyboard":
            try:
                data["output_data"]["human_text"] = parse_storyboard_json(data["output_data"].get("storyboard_text", ""))
            except Exception:
                pass
        elif stage_type == "image_generation":
            try:
                data["input_data"]["human_text"] = parse_storyboard_json(data["input_data"].get("storyboard_text", ""))
            except Exception:
                pass
        return data


class ProjectModelConfigSerializer(serializers.ModelSerializer):
    """项目模型配置序列化器"""

    load_balance_strategy_display = serializers.CharField(
        source='get_load_balance_strategy_display',
        read_only=True
    )

    # 显示模型提供商名称列表
    rewrite_providers_names = serializers.SerializerMethodField()
    storyboard_providers_names = serializers.SerializerMethodField()
    image_providers_names = serializers.SerializerMethodField()
    camera_providers_names = serializers.SerializerMethodField()
    video_providers_names = serializers.SerializerMethodField()

    class Meta:
        model = ProjectModelConfig
        fields = [
            'id', 'project', 'load_balance_strategy', 'load_balance_strategy_display',
            'rewrite_providers', 'rewrite_providers_names',
            'storyboard_providers', 'storyboard_providers_names',
            'image_providers', 'image_providers_names',
            'camera_providers', 'camera_providers_names',
            'video_providers', 'video_providers_names',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_rewrite_providers_names(self, obj):
        return [p.name for p in obj.rewrite_providers.all()]

    def get_storyboard_providers_names(self, obj):
        return [p.name for p in obj.storyboard_providers.all()]

    def get_image_providers_names(self, obj):
        return [p.name for p in obj.image_providers.all()]

    def get_camera_providers_names(self, obj):
        return [p.name for p in obj.camera_providers.all()]

    def get_video_providers_names(self, obj):
        return [p.name for p in obj.video_providers.all()]


class ProjectListSerializer(serializers.ModelSerializer):
    """项目列表序列化器 - 轻量级"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    prompt_set_name = serializers.CharField(source='prompt_template_set.name', read_only=True)

    # 统计信息
    stages_count = serializers.SerializerMethodField()
    completed_stages_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'original_topic',
            'status', 'status_display', 'user', 'user_name',
            'prompt_template_set', 'prompt_set_name',
            'stages_count', 'completed_stages_count',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'completed_at']

    def get_stages_count(self, obj):
        return obj.stages.count()

    def get_completed_stages_count(self, obj):
        return obj.stages.filter(status='completed').count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """项目详情序列化器 - 包含完整信息"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    prompt_set_name = serializers.CharField(source='prompt_template_set.name', read_only=True)

    # 嵌套序列化
    stages = ProjectStageSerializer(many=True, read_only=True)
    model_config = ProjectModelConfigSerializer(read_only=True)

    # 统计信息
    total_stages = serializers.SerializerMethodField()
    completed_stages = serializers.SerializerMethodField()
    failed_stages = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'original_topic',
            'status', 'status_display', 'user', 'user_name',
            'prompt_template_set', 'prompt_set_name',
            'stages', 'model_config',
            'total_stages', 'completed_stages', 'failed_stages', 'progress_percentage',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'completed_at']

    def get_total_stages(self, obj):
        return obj.stages.count()

    def get_completed_stages(self, obj):
        return obj.stages.filter(status='completed').count()

    def get_failed_stages(self, obj):
        return obj.stages.filter(status='failed').count()

    def get_progress_percentage(self, obj):
        total = obj.stages.count()
        if total == 0:
            return 0
        completed = obj.stages.filter(status='completed').count()
        return round((completed / total) * 100, 2)


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'original_topic',
            'prompt_template_set'
        ]
        read_only_fields = ['id']

    def validate_original_topic(self, value):
        """验证原始主题不能为空"""
        if not value or not value.strip():
            raise serializers.ValidationError("原始主题不能为空")
        return value.strip()

    def create(self, validated_data):
        """创建项目并初始化阶段"""
        # 从请求中获取用户
        user = self.context['request'].user
        validated_data['user'] = user

        # 创建项目
        project = Project.objects.create(**validated_data)

        # 初始化5个阶段(只创建阶段记录,不初始化 input_data/output_data)
        stage_types = ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
        for stage_type in stage_types:
            ProjectStage.objects.create(
                project=project,
                stage_type=stage_type,
                status='pending'
            )

        # 创建默认模型配置
        ProjectModelConfig.objects.create(project=project)

        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """项目更新序列化器"""

    class Meta:
        model = Project
        fields = ['name', 'description', 'original_topic', 'prompt_template_set', 'status']

    def validate_status(self, value):
        """验证状态转换的合法性"""
        instance = self.instance
        if instance:
            # 已完成的项目不能修改为其他状态
            if instance.status == 'completed' and value != 'completed':
                raise serializers.ValidationError("已完成的项目不能修改状态")

            # 只有暂停和草稿状态可以恢复处理
            if value == 'processing' and instance.status not in ['paused', 'draft']:
                raise serializers.ValidationError(f"项目状态为 {instance.get_status_display()} 时不能开始处理")

        return value


class StageRetrySerializer(serializers.Serializer):
    """阶段重试序列化器"""

    stage_name = serializers.ChoiceField(
        choices=['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
    )

    def validate_stage_name(self, value):
        """验证阶段是否存在且可重试"""
        project_id = self.context.get('project_id')
        if not project_id:
            raise serializers.ValidationError("缺少项目ID")

        try:
            stage = ProjectStage.objects.get(project_id=project_id, stage_type=value)
        except ProjectStage.DoesNotExist:
            raise serializers.ValidationError(f"阶段 {value} 不存在")

        # 检查重试次数
        if stage.retry_count >= stage.max_retries:
            raise serializers.ValidationError(
                f"阶段 {value} 已达到最大重试次数 ({stage.max_retries})"
            )

        return value


class StageExecuteSerializer(serializers.Serializer):
    """阶段执行序列化器"""

    stage_name = serializers.ChoiceField(
        choices=['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
    )
    input_data = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        """验证阶段执行的前置条件"""
        project_id = self.context.get('project_id')
        stage_name = attrs['stage_name']

        if not project_id:
            raise serializers.ValidationError("缺少项目ID")

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError("项目不存在")

        # 检查项目状态
        if project.status not in ['draft', 'processing', 'paused']:
            raise serializers.ValidationError(
                f"项目状态为 {project.get_status_display()} 时不能执行阶段"
            )

        # 检查阶段是否存在
        try:
            stage = ProjectStage.objects.get(project_id=project_id, stage_type=stage_name)
        except ProjectStage.DoesNotExist:
            raise serializers.ValidationError(f"阶段 {stage_name} 不存在")

        # 检查阶段状态
        # if stage.status == 'processing':
        #     raise serializers.ValidationError(f"阶段 {stage_name} 正在处理中")

        return attrs


class ProjectTemplateSerializer(serializers.Serializer):
    """项目模板序列化器"""

    template_name = serializers.CharField(max_length=255)
    include_model_config = serializers.BooleanField(default=True)

    def validate_template_name(self, value):
        """验证模板名称"""
        if not value or not value.strip():
            raise serializers.ValidationError("模板名称不能为空")
        return value.strip()
