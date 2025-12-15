"""
提示词管理序列化器
遵循单一职责原则(SRP): 每个序列化器只负责一个模型的序列化
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PromptTemplateSet, PromptTemplate, GlobalVariable
import re
import json
from jinja2 import Template, TemplateSyntaxError, Environment, meta

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器 - 仅用于嵌套展示"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields


class ModelProviderSerializer(serializers.Serializer):
    """模型提供商序列化器 - 仅用于嵌套展示"""
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    provider_type = serializers.CharField(read_only=True)
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    model_name = serializers.CharField(read_only=True)


class PromptTemplateSerializer(serializers.ModelSerializer):
    """
    提示词模板序列化器
    职责: 提示词模板的序列化和验证
    """

    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    extracted_variables = serializers.SerializerMethodField()
    model_provider_detail = ModelProviderSerializer(source='model_provider', read_only=True)

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'template_set', 'stage_type', 'stage_type_display',
            'model_provider', 'model_provider_detail',
            'template_content', 'variables', 'extracted_variables',
            'version', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def get_extracted_variables(self, obj):
        """
        自动提取模板中的变量
        使用Jinja2的AST解析提取所有变量
        """
        try:
            env = Environment()
            ast = env.parse(obj.template_content)
            variables = meta.find_undeclared_variables(ast)
            return list(variables)
        except Exception:
            return []

    def validate_template_content(self, value):
        """
        验证模板语法
        确保Jinja2模板语法正确
        """
        try:
            Template(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f'模板语法错误: {str(e)}')
        return value

    def validate_variables(self, value):
        """
        验证变量定义格式
        示例: {"topic": "string", "style": "string", "length": "int"}
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError('变量定义必须是字典格式')

        valid_types = ['string', 'int', 'float', 'bool', 'list', 'dict']
        for var_name, var_type in value.items():
            if not isinstance(var_name, str):
                raise serializers.ValidationError(f'变量名必须是字符串: {var_name}')
            if var_type not in valid_types:
                raise serializers.ValidationError(
                    f'变量类型 "{var_type}" 无效。有效类型: {", ".join(valid_types)}'
                )

        return value

    def validate(self, attrs):
        """
        交叉验证
        1. 确保模板中使用的变量在变量定义中存在
        2. 确保 model_provider 的类型与 stage_type 匹配
        3. 确保 template_set + stage_type 唯一性（排除自身）
        """
        template_content = attrs.get('template_content', '')
        variables = attrs.get('variables', {})
        stage_type = attrs.get('stage_type', self.instance.stage_type if self.instance else None)
        model_provider = attrs.get('model_provider')
        template_set = attrs.get('template_set', self.instance.template_set if self.instance else None)

        # 验证模板变量
        try:
            env = Environment()
            ast = env.parse(template_content)
            used_variables = meta.find_undeclared_variables(ast)

            # 检查未定义的变量
            undefined_vars = used_variables - set(variables.keys())
            if undefined_vars:
                raise serializers.ValidationError({
                    'variables': f'模板中使用了未定义的变量: {", ".join(undefined_vars)}'
                })
        except TemplateSyntaxError:
            # 语法错误已在 validate_template_content 中处理
            pass

        # 验证模型提供商类型匹配
        if model_provider and stage_type:
            # 定义阶段类型与模型类型的映射
            stage_to_provider_type = {
                'rewrite': 'llm',
                'storyboard': 'llm',
                'image_generation': 'text2image',
                'camera_movement': 'llm',
                'video_generation': 'image2video',
            }

            expected_type = stage_to_provider_type.get(stage_type)
            if expected_type and model_provider.provider_type != expected_type:
                raise serializers.ValidationError({
                    'model_provider': f'该阶段需要 {expected_type} 类型的模型，但选择的是 {model_provider.provider_type} 类型'
                })

        # 验证唯一性约束: template_set + stage_type
        if template_set and stage_type:
            queryset = PromptTemplate.objects.filter(
                template_set=template_set,
                stage_type=stage_type
            )
            # 如果是更新操作，排除当前实例
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    'stage_type': f'该提示词集中已存在 "{dict(PromptTemplate.STAGE_TYPES).get(stage_type)}" 类型的模板，请先删除或更新现有模板'
                })

        return attrs


class PromptTemplateListSerializer(serializers.ModelSerializer):
    """提示词模板列表序列化器 - 简化版本"""

    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    model_provider_detail = ModelProviderSerializer(source='model_provider', read_only=True)

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'stage_type', 'stage_type_display',
            'model_provider', 'model_provider_detail',
            'template_content', 'version', 'is_active', 'updated_at'
        ]


class PromptTemplateSetSerializer(serializers.ModelSerializer):
    """
    提示词集序列化器
    职责: 提示词集的序列化,包含嵌套的模板列表
    """

    created_by = UserSerializer(read_only=True)
    templates = PromptTemplateListSerializer(many=True, read_only=True)
    templates_count = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplateSet
        fields = [
            'id', 'name', 'description', 'is_active', 'is_default',
            'created_by', 'templates', 'templates_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_templates_count(self, obj):
        """获取模板数量"""
        return obj.templates.count()

    def validate(self, attrs):
        """验证提示词集"""
        # 如果设置为默认,确保用户有权限
        if attrs.get('is_default') and not self.context['request'].user.is_staff:
            raise serializers.ValidationError({
                'is_default': '只有管理员可以设置默认提示词集'
            })
        return attrs

    def create(self, validated_data):
        """创建提示词集时自动设置创建者"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PromptTemplateSetListSerializer(serializers.ModelSerializer):
    """提示词集列表序列化器 - 简化版本"""

    created_by = UserSerializer(read_only=True)
    templates_count = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplateSet
        fields = [
            'id', 'name', 'description', 'is_active', 'is_default',
            'created_by', 'templates_count', 'created_at', 'updated_at'
        ]

    def get_templates_count(self, obj):
        return obj.templates.count()


class PromptTemplateVersionSerializer(serializers.Serializer):
    """
    提示词模板版本序列化器
    用于版本历史和对比
    """

    version = serializers.IntegerField()
    template_content = serializers.CharField()
    variables = serializers.JSONField()
    created_at = serializers.DateTimeField()

    # 注意: 实际版本历史需要额外的PromptTemplateVersion模型
    # 或使用django-simple-history等版本控制库


class PromptTemplatePreviewSerializer(serializers.Serializer):
    """
    提示词预览序列化器
    用于预览模板渲染结果
    """

    variables = serializers.JSONField(
        help_text='变量值字典,例: {"topic": "科幻", "style": "赛博朋克"}'
    )

    def validate_variables(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('变量必须是字典格式')
        return value


class PromptTemplateValidateSerializer(serializers.Serializer):
    """
    提示词验证序列化器
    用于验证模板语法
    """

    template_content = serializers.CharField()

    def validate_template_content(self, value):
        try:
            Template(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f'模板语法错误: {str(e)}')
        return value


class PromptTemplateEvaluationSerializer(serializers.Serializer):
    """
    提示词效果评估序列化器
    用于AI评估提示词质量
    """

    score = serializers.FloatField(min_value=0, max_value=10)
    clarity = serializers.FloatField(min_value=0, max_value=10)
    specificity = serializers.FloatField(min_value=0, max_value=10)
    creativity = serializers.FloatField(min_value=0, max_value=10)
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text='优化建议列表'
    )
    strengths = serializers.ListField(
        child=serializers.CharField(),
        help_text='优点列表'
    )
    weaknesses = serializers.ListField(
        child=serializers.CharField(),
        help_text='缺点列表'
    )


class GlobalVariableSerializer(serializers.ModelSerializer):
    """
    全局变量序列化器
    职责: 全局变量的序列化和验证
    """

    created_by = UserSerializer(read_only=True)
    variable_type_display = serializers.CharField(source='get_variable_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = GlobalVariable
        fields = [
            'id', 'key', 'value', 'typed_value',
            'variable_type', 'variable_type_display',
            'scope', 'scope_display',
            'group', 'description', 'is_active',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_typed_value(self, obj):
        """获取类型转换后的值"""
        return obj.get_typed_value()

    def validate_key(self, value):
        """
        验证变量键
        1. 只能包含字母、数字、下划线
        2. 必须以字母或下划线开头
        3. 不能是Python保留字
        """
        import keyword

        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', value):
            raise serializers.ValidationError(
                '变量键只能包含字母、数字、下划线，且必须以字母或下划线开头'
            )

        if keyword.iskeyword(value):
            raise serializers.ValidationError(f'"{value}" 是Python保留字，不能作为变量键')

        return value

    def validate_value(self, value):
        """
        验证变量值
        根据变量类型验证值的格式
        """
        variable_type = self.initial_data.get('variable_type', 'string')

        if variable_type == 'number':
            try:
                float(value)
            except ValueError:
                raise serializers.ValidationError('数字类型的值必须是有效的数字')
        elif variable_type == 'boolean':
            if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                raise serializers.ValidationError(
                    '布尔类型的值必须是: true/false, 1/0, yes/no, on/off'
                )
        elif variable_type == 'json':
            try:
                json.loads(value)
            except json.JSONDecodeError as e:
                raise serializers.ValidationError(f'JSON格式错误: {str(e)}')

        return value

    def validate(self, attrs):
        """
        交叉验证
        1. 确保 key + created_by + scope 唯一性
        2. 系统级变量只能由管理员创建
        """
        key = attrs.get('key')
        scope = attrs.get('scope', 'user')
        request = self.context.get('request')

        # 验证系统级变量权限
        if scope == 'system' and request and not request.user.is_staff:
            raise serializers.ValidationError({
                'scope': '只有管理员可以创建系统级变量'
            })

        # 验证唯一性
        if key and request:
            queryset = GlobalVariable.objects.filter(
                key=key,
                created_by=request.user,
                scope=scope
            )
            # 如果是更新操作，排除当前实例
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError({
                    'key': f'变量键 "{key}" 在当前作用域下已存在'
                })

        return attrs

    def create(self, validated_data):
        """创建全局变量时自动设置创建者"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class GlobalVariableListSerializer(serializers.ModelSerializer):
    """全局变量列表序列化器 - 简化版本"""

    variable_type_display = serializers.CharField(source='get_variable_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = GlobalVariable
        fields = [
            'id', 'key', 'value', 'typed_value',
            'variable_type', 'variable_type_display',
            'scope', 'scope_display',
            'group', 'is_active', 'updated_at'
        ]

    def get_typed_value(self, obj):
        """获取类型转换后的值"""
        return obj.get_typed_value()


class GlobalVariableBatchSerializer(serializers.Serializer):
    """
    批量操作全局变量序列化器
    用于批量创建/更新变量
    """

    variables = serializers.ListField(
        child=serializers.DictField(),
        help_text='变量列表，每个元素包含: key, value, variable_type, scope, group, description'
    )

    def validate_variables(self, value):
        """验证变量列表"""
        if not value:
            raise serializers.ValidationError('变量列表不能为空')

        for var in value:
            if 'key' not in var or 'value' not in var:
                raise serializers.ValidationError('每个变量必须包含 key 和 value 字段')

        return value
