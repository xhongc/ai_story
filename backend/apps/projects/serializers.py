"""
项目管理序列化器
职责: 数据序列化与验证
遵循单一职责原则(SRP)
"""

from rest_framework import serializers

from apps.content.models import ContentRewrite
from apps.projects.utils import parse_storyboard_json
from .models import Project, ProjectStage, ProjectModelConfig, Series


class ProjectStageSerializer(serializers.ModelSerializer):
    """项目阶段序列化器 - 返回真实的领域模型数据"""

    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    domain_data = serializers.SerializerMethodField()

    class Meta:
        model = ProjectStage
        fields = [
            'id', 'project', 'stage_type', 'stage_type_display',
            'status', 'status_display', 'input_data', 'output_data',
            'retry_count', 'max_retries', 'error_message',
            'started_at', 'completed_at', 'created_at',
            'domain_data'
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
                    return {
                        'id': None,
                        'original_text': None,
                        'rewritten_text': None,
                        'model_provider': None,
                        'prompt_used': None,
                        'generation_metadata': None,
                        'created_at': None,
                        'updated_at': None,
                    }

            elif stage_type == 'storyboard':
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
                return {'storyboards': result}

            elif stage_type == 'camera_movement':
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
                return {'storyboards': result}

            elif stage_type == 'video_generation':
                from apps.content.models import GeneratedVideo
                storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')
                result = []
                for sb in storyboards:
                    videos = GeneratedVideo.objects.filter(
                        storyboard=sb
                    ).select_related('model_provider', 'image', 'camera_movement').order_by('-created_at')
                    result.append({
                        'storyboard_id': str(sb.id),
                        'sequence_number': sb.sequence_number,
                        'videos': [
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
                    })
                return {'storyboards': result}

            return instance.output_data or {}
        except Exception:
            return instance.output_data or {}


class ProjectModelConfigSerializer(serializers.ModelSerializer):
    """项目模型配置序列化器"""

    rewrite_providers_names = serializers.SerializerMethodField()
    storyboard_providers_names = serializers.SerializerMethodField()
    image_providers_names = serializers.SerializerMethodField()
    camera_providers_names = serializers.SerializerMethodField()
    video_providers_names = serializers.SerializerMethodField()

    class Meta:
        model = ProjectModelConfig
        fields = [
            'id', 'project', 'load_balance_strategy',
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
    series_name = serializers.CharField(source='series.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    stages_count = serializers.SerializerMethodField()
    completed_stages_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'display_name', 'description', 'original_topic',
            'series', 'series_name', 'episode_number', 'episode_title', 'sort_order',
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

    def get_display_name(self, obj):
        if obj.episode_title:
            return obj.episode_title
        return obj.name


class ProjectDetailSerializer(serializers.ModelSerializer):
    """项目详情序列化器 - 包含完整信息"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    prompt_set_name = serializers.CharField(source='prompt_template_set.name', read_only=True)
    series_name = serializers.CharField(source='series.name', read_only=True)
    display_name = serializers.SerializerMethodField()

    stages = ProjectStageSerializer(many=True, read_only=True)
    model_config = ProjectModelConfigSerializer(read_only=True)

    total_stages = serializers.SerializerMethodField()
    completed_stages = serializers.SerializerMethodField()
    failed_stages = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'display_name', 'description', 'original_topic',
            'series', 'series_name', 'episode_number', 'episode_title', 'sort_order',
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

    def get_display_name(self, obj):
        if obj.episode_title:
            return obj.episode_title
        return obj.name


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""

    class Meta:
        model = Project
        fields = [
            'id', 'series', 'name', 'description', 'episode_number', 'episode_title',
            'sort_order', 'original_topic', 'prompt_template_set'
        ]
        read_only_fields = ['id']

    def validate_original_topic(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('原始主题不能为空')
        return value.strip()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        series = attrs.get('series')
        episode_number = attrs.get('episode_number')
        episode_title = attrs.get('episode_title', '')

        if series and not attrs.get('name'):
            if episode_title:
                attrs['name'] = episode_title.strip()
            elif episode_number:
                attrs['name'] = f'第{episode_number}集'

        if series and attrs.get('sort_order', 0) == 0 and episode_number:
            attrs['sort_order'] = episode_number

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user

        project = Project.objects.create(**validated_data)

        stage_types = ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
        for stage_type in stage_types:
            ProjectStage.objects.create(
                project=project,
                stage_type=stage_type,
                status='pending'
            )

        ProjectModelConfig.objects.create(project=project)

        ContentRewrite.objects.create(
            project=project,
            original_text=project.original_topic
        )

        return project


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """项目更新序列化器"""

    class Meta:
        model = Project
        fields = [
            'name', 'description', 'original_topic', 'prompt_template_set', 'status',
            'series', 'episode_number', 'episode_title', 'sort_order'
        ]

    def validate_status(self, value):
        instance = self.instance
        if instance:
            if instance.status == 'completed' and value != 'completed':
                raise serializers.ValidationError('已完成的项目不能修改状态')

            if value == 'processing' and instance.status not in ['paused', 'draft']:
                raise serializers.ValidationError(f'项目状态为 {instance.get_status_display()} 时不能开始处理')

        return value


class SeriesListSerializer(serializers.ModelSerializer):
    """作品列表序列化器"""

    user_name = serializers.CharField(source='user.username', read_only=True)
    episodes_count = serializers.SerializerMethodField()
    completed_episodes_count = serializers.SerializerMethodField()

    class Meta:
        model = Series
        fields = [
            'id', 'name', 'description', 'user', 'user_name',
            'episodes_count', 'completed_episodes_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_episodes_count(self, obj):
        return obj.episodes.count()

    def get_completed_episodes_count(self, obj):
        return obj.episodes.filter(status='completed').count()


class SeriesDetailSerializer(serializers.ModelSerializer):
    """作品详情序列化器"""

    user_name = serializers.CharField(source='user.username', read_only=True)
    episodes = serializers.SerializerMethodField()
    episodes_count = serializers.SerializerMethodField()

    class Meta:
        model = Series
        fields = [
            'id', 'name', 'description', 'user', 'user_name',
            'episodes_count', 'episodes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_episodes(self, obj):
        episodes = obj.episodes.all().select_related('user', 'prompt_template_set', 'series').prefetch_related('stages').order_by('sort_order', 'episode_number', 'created_at')
        return ProjectListSerializer(episodes, many=True).data

    def get_episodes_count(self, obj):
        return obj.episodes.count()


class SeriesCreateSerializer(serializers.ModelSerializer):
    """作品创建序列化器"""

    class Meta:
        model = Series
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('作品名称不能为空')
        return value.strip()


class SeriesUpdateSerializer(serializers.ModelSerializer):
    """作品更新序列化器"""

    class Meta:
        model = Series
        fields = ['name', 'description']


class StageRetrySerializer(serializers.Serializer):
    """阶段重试序列化器"""

    stage_name = serializers.ChoiceField(
        choices=['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
    )

    def validate_stage_name(self, value):
        project_id = self.context.get('project_id')
        if not project_id:
            raise serializers.ValidationError('缺少项目ID')

        try:
            stage = ProjectStage.objects.get(project_id=project_id, stage_type=value)
        except ProjectStage.DoesNotExist:
            raise serializers.ValidationError(f'阶段 {value} 不存在')

        if stage.retry_count >= stage.max_retries:
            raise serializers.ValidationError(
                f'阶段 {value} 已达到最大重试次数 ({stage.max_retries})'
            )

        return value


class StageExecuteSerializer(serializers.Serializer):
    """阶段执行序列化器"""

    stage_name = serializers.ChoiceField(
        choices=['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
    )
    input_data = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        project_id = self.context.get('project_id')
        stage_name = attrs['stage_name']

        if not project_id:
            raise serializers.ValidationError('缺少项目ID')

        try:
            Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError('项目不存在')

        try:
            ProjectStage.objects.get(project_id=project_id, stage_type=stage_name)
        except ProjectStage.DoesNotExist:
            raise serializers.ValidationError(f'阶段 {stage_name} 不存在')

        return attrs


class ProjectTemplateSerializer(serializers.Serializer):
    """项目模板序列化器"""

    template_name = serializers.CharField(max_length=255)
    include_model_config = serializers.BooleanField(default=True)

    def validate_template_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('模板名称不能为空')
        return value.strip()
