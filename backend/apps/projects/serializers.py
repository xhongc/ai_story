"""
项目管理序列化器
职责: 数据序列化与验证
遵循单一职责原则(SRP)
"""

from django.db import transaction
from rest_framework import serializers

from apps.content.models import ContentRewrite
from apps.models.serializers import ModelProviderDetailSerializer
from apps.prompts.serializers import GlobalVariableListSerializer
from apps.projects.utils import parse_storyboard_json
from .models import EpisodeTaskQueue, Project, ProjectStage, ProjectModelConfig, ProjectAssetBinding, Series


def get_latest_episode(series):
    if not series:
        return None

    return (
        series.episodes
        .order_by('-sort_order', '-episode_number', '-created_at')
        .first()
    )


def initialize_project_resources(project):
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


@transaction.atomic
def create_project_with_resources(validated_data, user):
    validated_data['user'] = user

    series = validated_data.get('series')
    episode_number = validated_data.get('episode_number')
    if series:
        Series.objects.select_for_update().filter(pk=series.pk).first()
        if episode_number and Project.objects.filter(series=series, episode_number=episode_number).exists():
            raise serializers.ValidationError({'episode_number': f'作品内已存在第{episode_number}集'})

    project = Project.objects.create(**validated_data)
    initialize_project_resources(project)
    return project


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
    image_providers_detail = ModelProviderDetailSerializer(source='image_providers', many=True, read_only=True)
    video_providers_detail = ModelProviderDetailSerializer(source='video_providers', many=True, read_only=True)

    class Meta:
        model = ProjectModelConfig
        fields = [
            'id', 'project', 'load_balance_strategy',
            'rewrite_providers', 'rewrite_providers_names',
            'storyboard_providers', 'storyboard_providers_names',
            'image_providers', 'image_providers_names', 'image_providers_detail',
            'camera_providers', 'camera_providers_names',
            'video_providers', 'video_providers_names', 'video_providers_detail',
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


class ProjectAssetBindingSerializer(serializers.ModelSerializer):
    """项目资产绑定序列化器"""

    asset = GlobalVariableListSerializer(read_only=True)
    asset_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = ProjectAssetBinding
        fields = ['id', 'project', 'asset', 'asset_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']


class ProjectAssetBindingUpdateSerializer(serializers.Serializer):
    """项目资产绑定更新序列化器"""

    asset_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        help_text='项目绑定的资产ID列表'
    )


class ProjectListSerializer(serializers.ModelSerializer):
    """项目列表序列化器 - 轻量级"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    prompt_set_name = serializers.CharField(source='prompt_template_set.name', read_only=True)
    series_name = serializers.CharField(source='series.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    stages_count = serializers.SerializerMethodField()
    completed_stages_count = serializers.SerializerMethodField()
    queue_status = serializers.SerializerMethodField()
    queue_position = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'display_name', 'description', 'original_topic',
            'series', 'series_name', 'episode_number', 'episode_title', 'sort_order',
            'status', 'status_display', 'queue_status', 'queue_position', 'user', 'user_name',
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

    def _get_active_queue_task(self, obj):
        tasks = getattr(obj, '_prefetched_objects_cache', {}).get('queue_tasks')
        if tasks is not None:
            for task in tasks:
                if task.status in ['waiting', 'running']:
                    return task
            return None
        return obj.queue_tasks.filter(status__in=['waiting', 'running']).order_by('created_at').first()

    def get_queue_status(self, obj):
        queue_task = self._get_active_queue_task(obj)
        return queue_task.status if queue_task else None

    def get_queue_position(self, obj):
        queue_task = self._get_active_queue_task(obj)
        if not queue_task or not obj.series_id:
            return None
        return EpisodeTaskQueue.objects.filter(
            series_id=obj.series_id,
            status__in=['waiting', 'running'],
            created_at__lt=queue_task.created_at,
        ).count() + 1


class ProjectDetailSerializer(serializers.ModelSerializer):
    """项目详情序列化器 - 包含完整信息"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    prompt_set_name = serializers.CharField(source='prompt_template_set.name', read_only=True)
    series_name = serializers.CharField(source='series.name', read_only=True)
    display_name = serializers.SerializerMethodField()

    stages = ProjectStageSerializer(many=True, read_only=True)
    model_config = ProjectModelConfigSerializer(read_only=True)
    asset_bindings = ProjectAssetBindingSerializer(many=True, read_only=True)

    total_stages = serializers.SerializerMethodField()
    completed_stages = serializers.SerializerMethodField()
    failed_stages = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    queue_status = serializers.SerializerMethodField()
    queue_position = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'display_name', 'description', 'original_topic',
            'series', 'series_name', 'episode_number', 'episode_title', 'sort_order',
            'status', 'status_display', 'queue_status', 'queue_position', 'user', 'user_name',
            'prompt_template_set', 'prompt_set_name',
            'stages', 'model_config', 'asset_bindings',
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

    def _get_active_queue_task(self, obj):
        tasks = getattr(obj, '_prefetched_objects_cache', {}).get('queue_tasks')
        if tasks is not None:
            for task in tasks:
                if task.status in ['waiting', 'running']:
                    return task
            return None
        return obj.queue_tasks.filter(status__in=['waiting', 'running']).order_by('created_at').first()

    def get_queue_status(self, obj):
        queue_task = self._get_active_queue_task(obj)
        return queue_task.status if queue_task else None

    def get_queue_position(self, obj):
        queue_task = self._get_active_queue_task(obj)
        if not queue_task or not obj.series_id:
            return None
        return EpisodeTaskQueue.objects.filter(
            series_id=obj.series_id,
            status__in=['waiting', 'running'],
            created_at__lt=queue_task.created_at,
        ).count() + 1


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

        latest_episode = None
        if series:
            latest_episode = get_latest_episode(series)

            if not episode_number:
                last_episode_number = None
                if latest_episode:
                    last_episode_number = latest_episode.episode_number or latest_episode.sort_order or 0
                attrs['episode_number'] = (last_episode_number or 0) + 1
                episode_number = attrs['episode_number']

            elif Project.objects.filter(series=series, episode_number=episode_number).exists():
                raise serializers.ValidationError({'episode_number': f'作品内已存在第{episode_number}集'})

            if not attrs.get('prompt_template_set') and latest_episode and latest_episode.prompt_template_set:
                attrs['prompt_template_set'] = latest_episode.prompt_template_set

        if series and not attrs.get('name'):
            if episode_number:
                attrs['name'] = f'第{episode_number}集'

        if series and attrs.get('sort_order', 0) == 0 and episode_number:
            attrs['sort_order'] = episode_number

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        return create_project_with_resources(validated_data, user)


class BatchEpisodeCreateItemSerializer(serializers.Serializer):
    """批量创建单个分集项"""

    episode_title = serializers.CharField(max_length=255)
    original_topic = serializers.CharField()
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_episode_title(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('分集标题不能为空')
        return value

    def validate_original_topic(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('原始主题不能为空')
        return value

    def validate_name(self, value):
        return (value or '').strip()


class ProjectBatchCreateSerializer(serializers.Serializer):
    """批量创建分集序列化器"""

    series = serializers.PrimaryKeyRelatedField(queryset=Series.objects.all())
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    prompt_template_set = serializers.PrimaryKeyRelatedField(
        queryset=Project._meta.get_field('prompt_template_set').remote_field.model.objects.all(),
        required=False,
        allow_null=True,
    )
    start_episode_number = serializers.IntegerField(required=False, min_value=1)
    episodes = BatchEpisodeCreateItemSerializer(many=True, allow_empty=False)

    def validate_description(self, value):
        return (value or '').strip()

    def validate_episodes(self, value):
        if not value:
            raise serializers.ValidationError('请至少添加一个分集')
        if len(value) > 20:
            raise serializers.ValidationError('单次最多批量创建20集')
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        series = attrs['series']
        episodes = attrs['episodes']
        latest_episode = get_latest_episode(series)

        start_episode_number = attrs.get('start_episode_number')
        if not start_episode_number:
            last_episode_number = None
            if latest_episode:
                last_episode_number = latest_episode.episode_number or latest_episode.sort_order or 0
            start_episode_number = (last_episode_number or 0) + 1
            attrs['start_episode_number'] = start_episode_number

        if not attrs.get('prompt_template_set') and latest_episode and latest_episode.prompt_template_set:
            attrs['prompt_template_set'] = latest_episode.prompt_template_set

        target_numbers = [start_episode_number + index for index in range(len(episodes))]
        duplicated_numbers = []
        existing_numbers = set(
            Project.objects.filter(series=series, episode_number__in=target_numbers)
            .values_list('episode_number', flat=True)
        )
        for number in target_numbers:
            if number in existing_numbers:
                duplicated_numbers.append(number)

        if duplicated_numbers:
            duplicated_text = '、'.join(f'第{number}集' for number in duplicated_numbers)
            raise serializers.ValidationError({'start_episode_number': f'以下分集序号已存在：{duplicated_text}'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        series = validated_data['series']
        description = validated_data.get('description', '')
        prompt_template_set = validated_data.get('prompt_template_set')
        start_episode_number = validated_data['start_episode_number']
        episodes = validated_data['episodes']

        Series.objects.select_for_update().filter(pk=series.pk).first()

        target_numbers = [start_episode_number + index for index in range(len(episodes))]
        existing_numbers = set(
            Project.objects.filter(series=series, episode_number__in=target_numbers)
            .values_list('episode_number', flat=True)
        )
        if existing_numbers:
            duplicated_text = '、'.join(f'第{number}集' for number in sorted(existing_numbers))
            raise serializers.ValidationError({'start_episode_number': f'以下分集序号已存在：{duplicated_text}'})

        projects = []
        for index, episode_data in enumerate(episodes):
            episode_number = start_episode_number + index
            payload = {
                'series': series,
                'description': description,
                'prompt_template_set': prompt_template_set,
                'episode_number': episode_number,
                'episode_title': episode_data['episode_title'],
                'name': episode_data.get('name') or f'第{episode_number}集',
                'original_topic': episode_data['original_topic'],
                'sort_order': episode_number,
            }
            projects.append(create_project_with_resources(payload, user))

        return projects


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
