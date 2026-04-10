"""
提示词管理领域模型
遵循开闭原则(OCP): 提示词模板可扩展,无需修改核心代码
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PromptTemplateSet(models.Model):
    """
    提示词集
    职责: 组织和管理提示词模板集合
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=255)
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('是否激活', default=True)
    is_default = models.BooleanField('是否默认', default=False)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='prompt_sets'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_template_sets'
        verbose_name = '提示词集'
        verbose_name_plural = '提示词集'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_default']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """确保只有一个默认提示词集"""
        if self.is_default:
            PromptTemplateSet.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class PromptTemplate(models.Model):
    """
    提示词模板
    职责: 存储和管理单个阶段的提示词模板
    支持Jinja2模板语法
    """

    STAGE_TYPES = [
        ('rewrite', '剧本精修'),
        ('asset_extraction', '资产抽取'),
        ('storyboard', '分镜生成'),
        ('image_generation', '文生图'),
        ('multi_grid_image', '多宫格图片'),
        ('image_edit', '图片编辑'),
        ('camera_movement', '运镜生成'),
        ('video_generation', '图生视频'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_set = models.ForeignKey(
        PromptTemplateSet,
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name='提示词集'
    )

    stage_type = models.CharField('阶段类型', max_length=20, choices=STAGE_TYPES)

    # 关联的模型提供商 (该阶段使用的默认模型)
    model_provider = models.ForeignKey(
        'models.ModelProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_templates',
        verbose_name='模型提供商',
        help_text='该提示词模板默认使用的AI模型'
    )

    # 模板内容 (支持Jinja2语法)
    template_content = models.TextField('模板内容')

    # 变量定义 (JSON格式)
    # 示例: {"topic": "string", "style": "string", "length": "int"}
    variables = models.JSONField('变量定义', default=dict, blank=True)

    # 阶段执行参数 (JSON格式)
    # 示例: {"duration": 5, "fps": 24}
    client_params = models.JSONField('执行参数', default=dict, blank=True)

    # 版本控制
    version = models.IntegerField('版本', default=1)
    is_active = models.BooleanField('是否激活', default=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_templates'
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'
        constraints = [
            models.UniqueConstraint(
                fields=['template_set', 'stage_type'],
                condition=models.Q(is_active=True),
                name='uniq_active_template_per_stage'
            )
        ]
        indexes = [
            models.Index(fields=['template_set', 'stage_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.template_set.name} - {self.get_stage_type_display()}'


class GlobalVariable(models.Model):
    """
    全局变量
    职责: 存储可在所有提示词模板中使用的全局变量
    支持用户级和系统级作用域
    """

    VARIABLE_TYPES = [
        ('string', '字符串'),
        ('number', '数字'),
        ('boolean', '布尔值'),
        ('json', 'JSON对象'),
        ('image', '图片'),
    ]

    SCOPE_TYPES = [
        ('system', '系统级'),  # 所有用户可见
        ('user', '用户级'),    # 仅创建者可见
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField('变量键', max_length=100, db_index=True)
    value = models.TextField('变量值', blank=True, default='')
    image_file = models.ImageField(
        '图片文件',
        upload_to='assets/images/%Y/%m/',
        blank=True,
        null=True
    )
    variable_type = models.CharField(
        '变量类型',
        max_length=20,
        choices=VARIABLE_TYPES,
        default='string'
    )
    scope = models.CharField(
        '作用域',
        max_length=20,
        choices=SCOPE_TYPES,
        default='user'
    )
    group = models.CharField('分组', max_length=100, blank=True, default='')
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('是否激活', default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='创建者',
        related_name='global_variables'
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'global_variables'
        verbose_name = '全局变量'
        verbose_name_plural = '全局变量'
        ordering = ['group', 'key']
        unique_together = [('key', 'created_by', 'scope')]
        indexes = [
            models.Index(fields=['scope', 'is_active']),
            models.Index(fields=['created_by', 'is_active']),
            models.Index(fields=['group', 'is_active']),
        ]

    def __str__(self):
        return f'{self.key} ({self.get_scope_display()})'

    def get_typed_value(self):
        """
        根据变量类型返回正确类型的值

        Returns:
            转换后的值
        """
        import json

        if self.variable_type == 'number':
            try:
                # 尝试转换为整数
                if '.' not in self.value:
                    return int(self.value)
                # 否则转换为浮点数
                return float(self.value)
            except ValueError:
                return 0
        elif self.variable_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.variable_type == 'json':
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        elif self.variable_type == 'image':
            # 图片类型返回图片URL
            if self.image_file:
                return self.image_file.url
            return self.value or ''
        else:  # string
            return self.value

    @classmethod
    def get_variables_for_user(cls, user, include_system=True):
        """
        获取用户可用的所有变量

        Args:
            user: 用户对象
            include_system: 是否包含系统级变量

        Returns:
            变量字典 {key: typed_value}
        """
        from django.db.models import Q

        query = Q(created_by=user, scope='user', is_active=True)

        if include_system:
            query |= Q(scope='system', is_active=True)

        variables = {}
        for var in cls.objects.filter(query):
            variables[var.key] = var.get_typed_value()

        return variables


class PromptDebugSession(models.Model):
    """
    提示词调试会话
    职责: 挂载某个模板的可编辑调试草稿与最近输入状态
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='debug_sessions',
        verbose_name='提示词模板'
    )
    template_set = models.ForeignKey(
        PromptTemplateSet,
        on_delete=models.CASCADE,
        related_name='debug_sessions',
        verbose_name='提示词集'
    )
    name = models.CharField('会话名称', max_length=255, blank=True, default='')
    stage_type = models.CharField('阶段类型', max_length=20, choices=PromptTemplate.STAGE_TYPES)
    draft_template_content = models.TextField('草稿模板内容', blank=True, default='')
    draft_variables = models.JSONField('草稿变量定义', default=dict, blank=True)
    draft_client_params = models.JSONField('草稿执行参数', default=dict, blank=True)
    model_provider = models.ForeignKey(
        'models.ModelProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_debug_sessions',
        verbose_name='调试模型'
    )
    latest_variable_values = models.JSONField('最近变量值', default=dict, blank=True)
    latest_input_payload = models.JSONField('最近输入载荷', default=dict, blank=True)
    latest_source_artifact = models.ForeignKey(
        'PromptDebugArtifact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referenced_by_sessions',
        verbose_name='最近引用资产'
    )
    last_run_at = models.DateTimeField('最近运行时间', null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_debug_sessions',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_debug_sessions'
        verbose_name = '提示词调试会话'
        verbose_name_plural = '提示词调试会话'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['created_by', 'stage_type']),
            models.Index(fields=['prompt_template', '-updated_at']),
        ]

    def __str__(self):
        return self.name or f'{self.prompt_template} 调试会话'


class PromptDebugRun(models.Model):
    """
    提示词调试运行记录
    职责: 保存某次调试执行的输入、渲染结果与输出
    """

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        PromptDebugSession,
        on_delete=models.CASCADE,
        related_name='runs',
        verbose_name='调试会话'
    )
    stage_type = models.CharField('阶段类型', max_length=20, choices=PromptTemplate.STAGE_TYPES)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    source_artifact = models.ForeignKey(
        'PromptDebugArtifact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_runs',
        verbose_name='来源资产'
    )
    model_provider = models.ForeignKey(
        'models.ModelProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_debug_runs',
        verbose_name='使用模型'
    )
    template_snapshot = models.TextField('模板快照', blank=True, default='')
    variable_values = models.JSONField('变量值', default=dict, blank=True)
    input_payload = models.JSONField('输入载荷', default=dict, blank=True)
    resolved_variables = models.JSONField('解析后变量', default=dict, blank=True)
    rendered_prompt = models.TextField('渲染后提示词', blank=True, default='')
    raw_response = models.JSONField('原始响应', default=dict, blank=True)
    parsed_output = models.JSONField('解析后输出', default=dict, blank=True)
    latency_ms = models.IntegerField('延迟(毫秒)', default=0)
    error_message = models.TextField('错误信息', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_debug_runs'
        verbose_name = '提示词调试运行'
        verbose_name_plural = '提示词调试运行'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['stage_type', 'status']),
        ]

    def __str__(self):
        return f'{self.session} - {self.created_at:%Y-%m-%d %H:%M:%S}'


class PromptDebugArtifact(models.Model):
    """
    调试资产
    职责: 保存调试输出中可被下游阶段复用的中间结果
    """

    ARTIFACT_TYPES = [
        ('text', '文本'),
        ('storyboard_bundle', '分镜集合'),
        ('storyboard_item', '分镜条目'),
        ('image', '图片'),
        ('video', '视频'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        PromptDebugRun,
        on_delete=models.CASCADE,
        related_name='artifacts',
        verbose_name='调试运行'
    )
    source_artifact = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='来源资产'
    )
    artifact_type = models.CharField('资产类型', max_length=30, choices=ARTIFACT_TYPES)
    stage_type = models.CharField('阶段类型', max_length=20, choices=PromptTemplate.STAGE_TYPES)
    name = models.CharField('名称', max_length=255)
    sequence_number = models.IntegerField('序号', null=True, blank=True)
    content = models.JSONField('资产内容', default=dict, blank=True)
    preview_text = models.TextField('预览文本', blank=True, default='')
    preview_image_url = models.URLField('预览图片', max_length=1024, blank=True, default='')
    preview_video_url = models.URLField('预览视频', max_length=1024, blank=True, default='')
    is_pinned = models.BooleanField('是否固定', default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prompt_debug_artifacts',
        verbose_name='创建者'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'prompt_debug_artifacts'
        verbose_name = '提示词调试资产'
        verbose_name_plural = '提示词调试资产'
        ordering = ['stage_type', 'sequence_number', '-created_at']
        indexes = [
            models.Index(fields=['created_by', 'artifact_type']),
            models.Index(fields=['stage_type', 'artifact_type']),
            models.Index(fields=['run', 'sequence_number']),
        ]

    def __str__(self):
        return self.name
