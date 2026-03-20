"""
模型管理序列化器
职责: 数据序列化与验证
遵循单一职责原则(SRP)
"""

from rest_framework import serializers
from .models import ModelProvider, ModelUsageLog, VendorConnectionConfig
from .vendor_catalog import VENDOR_CATALOG


class ModelProviderListSerializer(serializers.ModelSerializer):
    """模型提供商列表序列化器 - 轻量级"""

    provider_type_display = serializers.CharField(
        source='get_provider_type_display',
        read_only=True
    )

    # 统计信息
    total_usage_count = serializers.SerializerMethodField()
    recent_usage_count = serializers.SerializerMethodField()

    class Meta:
        model = ModelProvider
        fields = [
            'id', 'name', 'provider_type', 'provider_type_display',
            'model_name', 'executor_class', 'is_active', 'priority',
            'total_usage_count', 'recent_usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_usage_count(self, obj):
        """获取总使用次数"""
        return obj.usage_logs.count()

    def get_recent_usage_count(self, obj):
        """获取最近7天使用次数"""
        from django.utils import timezone
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)
        return obj.usage_logs.filter(created_at__gte=seven_days_ago).count()


class ModelProviderDetailSerializer(serializers.ModelSerializer):
    """模型提供商详情序列化器 - 完整信息"""

    provider_type_display = serializers.CharField(
        source='get_provider_type_display',
        read_only=True
    )

    # 统计信息
    total_usage_count = serializers.SerializerMethodField()
    success_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    avg_latency_ms = serializers.SerializerMethodField()
    total_tokens_used = serializers.SerializerMethodField()

    class Meta:
        model = ModelProvider
        fields = [
            'id', 'name', 'provider_type', 'provider_type_display',
            'api_url', 'api_key', 'model_name', 'executor_class',
            # LLM专用参数
            'max_tokens', 'temperature', 'top_p',
            # 通用参数
            'timeout', 'is_active', 'priority',
            # 限流配置
            'rate_limit_rpm', 'rate_limit_rpd',
            # 额外配置
            'extra_config',
            # 统计信息
            'total_usage_count', 'success_count', 'failed_count',
            'success_rate', 'avg_latency_ms', 'total_tokens_used',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """隐藏API Key的完整内容"""
        data = super().to_representation(instance)
        return data

    def get_total_usage_count(self, obj):
        """获取总使用次数"""
        return obj.usage_logs.count()

    def get_success_count(self, obj):
        """获取成功次数"""
        return obj.usage_logs.filter(status='success').count()

    def get_failed_count(self, obj):
        """获取失败次数"""
        return obj.usage_logs.filter(status='failed').count()

    def get_success_rate(self, obj):
        """获取成功率"""
        total = obj.usage_logs.count()
        if total == 0:
            return 0.0
        success = obj.usage_logs.filter(status='success').count()
        return round((success / total) * 100, 2)

    def get_avg_latency_ms(self, obj):
        """获取平均延迟"""
        from django.db.models import Avg
        result = obj.usage_logs.aggregate(avg_latency=Avg('latency_ms'))
        return round(result['avg_latency'] or 0, 2)

    def get_total_tokens_used(self, obj):
        """获取总Token使用量"""
        from django.db.models import Sum
        result = obj.usage_logs.aggregate(total_tokens=Sum('tokens_used'))
        return result['total_tokens'] or 0


class ModelProviderCreateSerializer(serializers.ModelSerializer):
    """模型提供商创建序列化器"""

    class Meta:
        model = ModelProvider
        fields = [
            'name', 'provider_type', 'api_url', 'api_key', 'model_name',
            'executor_class',
            'max_tokens', 'temperature', 'top_p',
            'timeout', 'is_active', 'priority',
            'rate_limit_rpm', 'rate_limit_rpd',
            'extra_config'
        ]

    def validate_api_url(self, value):
        """验证API URL格式"""
        if not value or not value.strip():
            raise serializers.ValidationError("API URL不能为空")
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("API URL必须以http://或https://开头")
        return value.strip()

    def validate_api_key(self, value):
        """验证API Key"""
        if not value or not value.strip():
            raise serializers.ValidationError("API Key不能为空")
        return value.strip()

    def validate_temperature(self, value):
        """验证温度参数"""
        if value < 0 or value > 2:
            raise serializers.ValidationError("温度参数必须在0-2之间")
        return value

    def validate_top_p(self, value):
        """验证Top P参数"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Top P参数必须在0-1之间")
        return value

    def validate_priority(self, value):
        """验证优先级"""
        if value < 0:
            raise serializers.ValidationError("优先级不能为负数")
        return value

    def validate(self, attrs):
        """交叉验证"""
        provider_type = attrs.get('provider_type')

        # 根据提供商类型验证必要配置
        if provider_type == 'llm':
            # LLM模型需要配置max_tokens和temperature
            if attrs.get('max_tokens', 0) <= 0:
                raise serializers.ValidationError({
                    'max_tokens': 'LLM模型必须配置有效的max_tokens'
                })

        elif provider_type == 'text2image':
            # 文生图模型建议配置extra_config中的图片参数
            extra_config = attrs.get('extra_config', {})
            if not extra_config.get('width') or not extra_config.get('height'):
                # 设置默认值
                if not extra_config.get('width'):
                    extra_config['width'] = 1024
                if not extra_config.get('height'):
                    extra_config['height'] = 1024
                attrs['extra_config'] = extra_config

        elif provider_type == 'image2video':
            # 图生视频模型建议配置extra_config中的视频参数
            extra_config = attrs.get('extra_config', {})
            if not extra_config.get('fps'):
                extra_config['fps'] = 24
            if not extra_config.get('duration'):
                extra_config['duration'] = 5
            attrs['extra_config'] = extra_config

        elif provider_type == 'image_edit':
            # 图片编辑模型建议配置extra_config中的基础图片参数
            extra_config = attrs.get('extra_config', {})
            if not extra_config.get('width'):
                extra_config['width'] = 1024
            if not extra_config.get('height'):
                extra_config['height'] = 1024
            if extra_config.get('strength') is None:
                extra_config['strength'] = 0.35
            attrs['extra_config'] = extra_config

        return attrs


class ModelProviderUpdateSerializer(serializers.ModelSerializer):
    """模型提供商更新序列化器"""

    class Meta:
        model = ModelProvider
        fields = [
            'name', 'api_url', 'api_key', 'model_name',
            'executor_class',
            'max_tokens', 'temperature', 'top_p',
            'timeout', 'is_active', 'priority',
            'rate_limit_rpm', 'rate_limit_rpd',
            'extra_config'
        ]

    def validate_api_url(self, value):
        """验证API URL格式"""
        if not value or not value.strip():
            raise serializers.ValidationError("API URL不能为空")
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("API URL必须以http://或https://开头")
        return value.strip()

    def validate_api_key(self, value):
        """验证API Key"""
        if not value or not value.strip():
            raise serializers.ValidationError("API Key不能为空")
        return value.strip()

    def validate_temperature(self, value):
        """验证温度参数"""
        if value < 0 or value > 2:
            raise serializers.ValidationError("温度参数必须在0-2之间")
        return value

    def validate_top_p(self, value):
        """验证Top P参数"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Top P参数必须在0-1之间")
        return value

    def validate_priority(self, value):
        """验证优先级"""
        if value < 0:
            raise serializers.ValidationError("优先级不能为负数")
        return value


class ModelProviderSimpleSerializer(serializers.ModelSerializer):
    """模型提供商简化序列化器 - 仅返回id和name,用于下拉选择"""

    class Meta:
        model = ModelProvider
        fields = ['id', 'name']
        read_only_fields = ['id', 'name']


class ModelUsageLogSerializer(serializers.ModelSerializer):
    """模型使用日志序列化器"""

    model_provider_name = serializers.CharField(
        source='model_provider.name',
        read_only=True
    )
    model_provider_type = serializers.CharField(
        source='model_provider.provider_type',
        read_only=True
    )

    class Meta:
        model = ModelUsageLog
        fields = [
            'id', 'model_provider', 'model_provider_name', 'model_provider_type',
            'request_data', 'response_data',
            'tokens_used', 'latency_ms', 'status', 'error_message',
            'project_id', 'stage_type',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ModelProviderTestSerializer(serializers.Serializer):
    """模型提供商测试连接序列化器"""

    test_prompt = serializers.CharField(
        required=False,
        default="Hello, this is a test.",
        help_text="测试用的提示词"
    )
    test_image_url = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='测试用图片URL，图生视频模型可传'
    )
    test_image_base64 = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='测试用图片base64，支持传入 data URL 或纯base64'
    )
    test_image_mime_type = serializers.CharField(
        required=False,
        allow_blank=True,
        default='image/jpeg',
        help_text='测试图片 MIME 类型'
    )

    def validate(self, attrs):
        """验证模型提供商配置"""
        provider_id = self.context.get('provider_id')
        if not provider_id:
            raise serializers.ValidationError("缺少模型提供商ID")

        try:
            provider = ModelProvider.objects.get(id=provider_id)
        except ModelProvider.DoesNotExist:
            raise serializers.ValidationError("模型提供商不存在")

        if not provider.is_active:
            raise serializers.ValidationError("模型提供商未激活")

        test_image_base64 = (attrs.get('test_image_base64') or '').strip()
        mime_type = (attrs.get('test_image_mime_type') or 'image/jpeg').strip() or 'image/jpeg'

        if test_image_base64.startswith('data:') and ';base64,' in test_image_base64:
            header, encoded = test_image_base64.split(';base64,', 1)
            mime_type = header.split(':', 1)[1] if ':' in header else mime_type
            test_image_base64 = encoded.strip()

        attrs['test_image_url'] = (attrs.get('test_image_url') or '').strip()
        attrs['test_image_base64'] = test_image_base64
        attrs['test_image_mime_type'] = mime_type

        attrs['provider'] = provider
        return attrs


class VendorModelDiscoverySerializer(serializers.Serializer):
    """厂商模型发现请求。"""

    vendor = serializers.ChoiceField(choices=[(key, value['label']) for key, value in VENDOR_CATALOG.items()])
    capability = serializers.ChoiceField(choices=ModelProvider.PROVIDER_TYPES)
    api_key = serializers.CharField(required=True, trim_whitespace=True)
    api_url = serializers.URLField(required=False, allow_blank=True)

    def validate_api_key(self, value):
        if not value:
            raise serializers.ValidationError('API Key不能为空')
        return value

    def validate(self, attrs):
        vendor_config = VENDOR_CATALOG.get(attrs['vendor'], {})
        capabilities = vendor_config.get('capabilities', {})
        if attrs['capability'] not in capabilities:
            raise serializers.ValidationError({'capability': '当前厂商不支持该模型能力'})
        capability_config = capabilities[attrs['capability']]
        return attrs


class VendorModelBatchCreateSerializer(serializers.Serializer):
    """厂商模型批量创建请求。"""

    vendor = serializers.ChoiceField(choices=[(key, value['label']) for key, value in VENDOR_CATALOG.items()])
    capability = serializers.ChoiceField(choices=ModelProvider.PROVIDER_TYPES)
    api_key = serializers.CharField(required=True, trim_whitespace=True)
    api_url = serializers.URLField(required=False, allow_blank=True)
    model_names = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        allow_empty=False,
    )
    is_active = serializers.BooleanField(required=False, default=True)
    timeout = serializers.IntegerField(required=False, min_value=1, max_value=600, default=60)
    max_tokens = serializers.IntegerField(required=False, min_value=1, default=4096)
    temperature = serializers.FloatField(required=False, min_value=0, max_value=2, default=0.7)
    top_p = serializers.FloatField(required=False, min_value=0, max_value=1, default=1.0)
    rate_limit_rpm = serializers.IntegerField(required=False, min_value=1, default=60)
    rate_limit_rpd = serializers.IntegerField(required=False, min_value=1, default=1000)
    priority = serializers.IntegerField(required=False, min_value=0, default=0)

    def validate_api_key(self, value):
        if not value:
            raise serializers.ValidationError('API Key不能为空')
        return value

    def validate_model_names(self, value):
        cleaned_names = []
        seen = set()
        for item in value:
            model_name = item.strip()
            if not model_name:
                continue
            if model_name in seen:
                continue
            seen.add(model_name)
            cleaned_names.append(model_name)

        if not cleaned_names:
            raise serializers.ValidationError('至少选择一个模型')

        return cleaned_names

    def validate(self, attrs):
        vendor_config = VENDOR_CATALOG.get(attrs['vendor'], {})
        capabilities = vendor_config.get('capabilities', {})
        if attrs['capability'] not in capabilities:
            raise serializers.ValidationError({'capability': '当前厂商不支持该模型能力'})
        capability_config = capabilities[attrs['capability']]
        return attrs


class VendorConnectionConfigSerializer(serializers.ModelSerializer):
    """厂商导入连接配置序列化器。"""

    vendor = serializers.ChoiceField(choices=[(key, value['label']) for key, value in VENDOR_CATALOG.items()])
    capability = serializers.ChoiceField(choices=ModelProvider.PROVIDER_TYPES)

    class Meta:
        model = VendorConnectionConfig
        fields = [
            'vendor', 'capability', 'api_key', 'api_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_api_key(self, value):
        return (value or '').strip()

    def validate_api_url(self, value):
        return (value or '').strip()

    def validate(self, attrs):
        vendor_config = VENDOR_CATALOG.get(attrs['vendor'], {})
        capabilities = vendor_config.get('capabilities', {})
        if attrs['capability'] not in capabilities:
            raise serializers.ValidationError({'capability': '当前厂商不支持该模型能力'})
        return attrs


class VendorConnectionConfigQuerySerializer(serializers.Serializer):
    """厂商导入连接配置查询参数。"""

    vendor = serializers.ChoiceField(choices=[(key, value['label']) for key, value in VENDOR_CATALOG.items()])
    capability = serializers.ChoiceField(choices=ModelProvider.PROVIDER_TYPES)

    def validate(self, attrs):
        vendor_config = VENDOR_CATALOG.get(attrs['vendor'], {})
        capabilities = vendor_config.get('capabilities', {})
        if attrs['capability'] not in capabilities:
            raise serializers.ValidationError({'capability': '当前厂商不支持该模型能力'})
        return attrs
