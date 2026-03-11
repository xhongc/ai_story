"""
项目管理领域模型
遵循单一职责原则(SRP)
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Series(models.Model):
    """
    作品/系列聚合根
    职责: 管理顶层作品信息,组织多个分集项目
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('作品名称', max_length=255)
    description = models.TextField('作品描述', blank=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='series_projects'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'series'
        verbose_name = '作品'
        verbose_name_plural = '作品'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    项目聚合根
    职责: 管理项目生命周期和基本信息
    """

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('paused', '已暂停'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('项目名称', max_length=255)
    description = models.TextField('项目描述', blank=True)

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='episodes',
        verbose_name='所属作品',
        null=True,
        blank=True
    )
    episode_number = models.IntegerField('分集序号', null=True, blank=True)
    episode_title = models.CharField('分集标题', max_length=255, blank=True, default='')
    sort_order = models.IntegerField('排序值', default=0)

    # 业务字段
    original_topic = models.TextField('原始主题')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    jianying_draft_path = models.CharField('剪映草稿路径', max_length=500, blank=True, default='')

    # 关联配置
    prompt_template_set = models.ForeignKey(
        'prompts.PromptTemplateSet',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='提示词集',
        related_name='projects'
    )

    # 所有者
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='projects'
    )

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)

    class Meta:
        db_table = 'projects'
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['series', 'sort_order', 'episode_number']),
        ]

    def __str__(self):
        return self.name


class ProjectStage(models.Model):
    """
    项目阶段
    职责: 追踪工作流各阶段状态
    """

    STAGE_TYPES = [
        ('rewrite', '文案改写'),
        ('storyboard', '分镜生成'),
        ('image_generation', '文生图'),
        ('camera_movement', '运镜生成'),
        ('video_generation', '图生视频'),
    ]

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('skipped', '已跳过'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name='项目'
    )

    stage_type = models.CharField('阶段类型', max_length=20, choices=STAGE_TYPES)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')

    # 数据字段
    input_data = models.JSONField('输入数据', default=dict, blank=True)
    output_data = models.JSONField('输出数据', default=dict, blank=True)

    # 重试机制
    retry_count = models.IntegerField('重试次数', default=0)
    max_retries = models.IntegerField('最大重试次数', default=3)
    error_message = models.TextField('错误信息', blank=True)

    # 时间戳
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'project_stages'
        verbose_name = '项目阶段'
        verbose_name_plural = '项目阶段'
        unique_together = [('project', 'stage_type')]
        ordering = ['created_at']

    def __str__(self):
        return f'{self.project.name} - {self.get_stage_type_display()}'


class ProjectModelConfig(models.Model):
    """
    项目模型配置
    职责: 管理项目使用的AI模型配置
    """

    LOAD_BALANCE_STRATEGIES = [
        ('round_robin', '轮询'),
        ('random', '随机'),
        ('weighted', '权重随机'),
        ('least_loaded', '最少负载'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='model_config',
        verbose_name='项目'
    )

    # 负载均衡策略
    load_balance_strategy = models.CharField(
        '负载均衡策略',
        max_length=20,
        choices=LOAD_BALANCE_STRATEGIES,
        default='weighted'
    )

    # 模型关联 - 使用ManyToMany支持多模型配置
    rewrite_providers = models.ManyToManyField(
        'models.ModelProvider',
        related_name='rewrite_configs',
        verbose_name='文案改写模型',
        blank=True
    )

    storyboard_providers = models.ManyToManyField(
        'models.ModelProvider',
        related_name='storyboard_configs',
        verbose_name='分镜生成模型',
        blank=True
    )

    image_providers = models.ManyToManyField(
        'models.ModelProvider',
        related_name='image_configs',
        verbose_name='文生图模型',
        blank=True
    )

    camera_providers = models.ManyToManyField(
        'models.ModelProvider',
        related_name='camera_configs',
        verbose_name='运镜生成模型',
        blank=True
    )

    video_providers = models.ManyToManyField(
        'models.ModelProvider',
        related_name='video_configs',
        verbose_name='图生视频模型',
        blank=True
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'project_model_configs'
        verbose_name = '项目模型配置'
        verbose_name_plural = '项目模型配置'

    def __str__(self):
        return f'{self.project.name} - 模型配置'


class ProjectAssetBinding(models.Model):
    """
    项目资产绑定
    职责: 管理项目在画布和模板中显式使用的资产集合
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='asset_bindings',
        verbose_name='项目'
    )
    asset = models.ForeignKey(
        'prompts.GlobalVariable',
        on_delete=models.CASCADE,
        related_name='project_bindings',
        verbose_name='资产'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'project_asset_bindings'
        verbose_name = '项目资产绑定'
        verbose_name_plural = '项目资产绑定'
        ordering = ['created_at']
        unique_together = [('project', 'asset')]
        indexes = [
            models.Index(fields=['project', 'created_at']),
        ]

    def __str__(self):
        return f'{self.project.name} - {self.asset.key}'
