"""
模型管理领域模型
遵循依赖倒置原则(DIP): 依赖抽象的ModelProvider,而非具体实现
"""

import uuid
from django.db import models


class ModelProvider(models.Model):
    """
    模型提供商
    职责: 存储AI模型的配置信息
    """

    PROVIDER_TYPES = [
        ('llm', 'LLM模型'),
        ('text2image', '文生图模型'),
        ('image2video', '图生视频模型'),
    ]

    # 执行器选项定义
    LLM_EXECUTORS = [
        ('core.ai_client.openai_client.OpenAIClient', 'OpenAI兼容客户端'),
        ('core.ai_client.mock_llm_client.MockLLMClient', 'Mock LLM客户端（测试用）'),
    ]

    TEXT2IMAGE_EXECUTORS = [
        ('core.ai_client.text2image_client.Text2ImageClient', '文生图客户端'),
        ('core.ai_client.comfyui_client.ComfyUIClient', 'ComfyUI客户端'),
        ('core.ai_client.mock_text2image_client.MockText2ImageClient', 'Mock 文生图客户端（测试用）'),
    ]

    IMAGE2VIDEO_EXECUTORS = [
        ('core.ai_client.image2video_client.Image2VideoClient', '图生视频客户端'),
        ('core.ai_client.comfyui_client.ComfyUIClient', 'ComfyUI客户端'),
        ('core.ai_client.mock_image2video_client.MockImage2VideoClient', 'Mock 图生视频客户端（测试用）'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('名称', max_length=255)
    provider_type = models.CharField('模型作用分类', max_length=20, choices=PROVIDER_TYPES)
    executor_class = models.CharField(
        '执行器类',
        max_length=255,
        help_text='执行器的完整类路径，如: core.ai_client.openai_client.OpenAIClient',
        blank=True,
        default=''
    )

    # API配置
    api_url = models.URLField('API地址')
    api_key = models.CharField('API密钥', max_length=512)  # 后续加密存储
    model_name = models.CharField('模型名称', max_length=255)

    # LLM专用参数
    max_tokens = models.IntegerField('最大Token数', default=2000)
    temperature = models.FloatField('温度', default=0.7)
    top_p = models.FloatField('Top P', default=1.0)

    # 通用参数
    timeout = models.IntegerField('超时时间(秒)', default=60)
    is_active = models.BooleanField('是否激活', default=True)
    priority = models.IntegerField('优先级/权重', default=0, help_text='用于负载均衡')

    # 限流配置
    rate_limit_rpm = models.IntegerField('每分钟请求数限制', default=60)
    rate_limit_rpd = models.IntegerField('每天请求数限制', default=1000)

    # 额外配置 (JSON格式,存储特定模型的额外参数)
    extra_config = models.JSONField('额外配置', default=dict, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'model_providers'
        verbose_name = '模型提供商'
        verbose_name_plural = '模型提供商'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['provider_type', 'is_active', '-priority']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_provider_type_display()})'

    def get_executor_choices(self):
        """
        根据provider_type返回对应的执行器选项

        Returns:
            list: 执行器选项列表
        """
        executor_map = {
            'llm': self.LLM_EXECUTORS,
            'text2image': self.TEXT2IMAGE_EXECUTORS,
            'image2video': self.IMAGE2VIDEO_EXECUTORS,
        }
        return executor_map.get(self.provider_type, [])

    def get_default_executor(self):
        """
        获取当前provider_type的默认执行器类路径

        Returns:
            str: 默认执行器类路径
        """
        choices = self.get_executor_choices()
        if choices:
            return choices[0][0]  # 返回第一个选项的值
        return ''

    def validate_executor_class(self):
        """
        验证executor_class是否在允许的选项中

        Returns:
            bool: 是否有效
        """
        if not self.executor_class:
            return False

        valid_executors = [choice[0] for choice in self.get_executor_choices()]
        return self.executor_class in valid_executors


class ModelUsageLog(models.Model):
    """
    模型使用日志
    职责: 记录模型调用历史,用于统计和成本计算
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.CASCADE,
        related_name='usage_logs',
        verbose_name='模型提供商'
    )

    # 使用信息
    request_data = models.JSONField('请求数据', default=dict)
    response_data = models.JSONField('响应数据', default=dict)

    # 统计信息
    tokens_used = models.IntegerField('使用Token数', default=0)
    latency_ms = models.IntegerField('延迟(毫秒)', default=0)
    status = models.CharField('状态', max_length=20, default='success')
    error_message = models.TextField('错误信息', blank=True)

    # 关联信息
    project_id = models.UUIDField('项目ID', null=True, blank=True)
    stage_type = models.CharField('阶段类型', max_length=20, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'model_usage_logs'
        verbose_name = '模型使用日志'
        verbose_name_plural = '模型使用日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_provider', '-created_at']),
            models.Index(fields=['project_id', 'stage_type']),
        ]

    def __str__(self):
        return f'{self.model_provider.name} - {self.created_at}'
