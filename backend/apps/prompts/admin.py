"""提示词管理Admin配置"""
from django.contrib import admin
from .models import (
    PromptTemplateSet,
    PromptTemplate,
    GlobalVariable,
    PromptDebugSession,
    PromptDebugRun,
    PromptDebugArtifact,
)


@admin.register(PromptTemplateSet)
class PromptTemplateSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_default', 'created_by', 'created_at']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'description']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_set', 'stage_type', 'version', 'is_active', 'created_at']
    list_filter = ['stage_type', 'is_active']
    search_fields = ['template_content']


@admin.register(GlobalVariable)
class GlobalVariableAdmin(admin.ModelAdmin):
    list_display = ['key', 'variable_type', 'scope', 'group', 'is_active', 'created_by', 'created_at']
    list_filter = ['variable_type', 'scope', 'group', 'is_active']
    search_fields = ['key', 'description', 'value']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('key', 'value', 'variable_type', 'description')
        }),
        ('作用域和分组', {
            'fields': ('scope', 'group', 'is_active')
        }),
        ('元数据', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PromptDebugSession)
class PromptDebugSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage_type', 'prompt_template', 'model_provider', 'created_by', 'last_run_at']
    list_filter = ['stage_type']
    search_fields = ['name', 'prompt_template__template_content']


@admin.register(PromptDebugRun)
class PromptDebugRunAdmin(admin.ModelAdmin):
    list_display = ['session', 'stage_type', 'status', 'model_provider', 'latency_ms', 'created_at']
    list_filter = ['stage_type', 'status']
    search_fields = ['rendered_prompt', 'error_message']


@admin.register(PromptDebugArtifact)
class PromptDebugArtifactAdmin(admin.ModelAdmin):
    list_display = ['name', 'artifact_type', 'stage_type', 'run', 'sequence_number', 'created_by', 'created_at']
    list_filter = ['artifact_type', 'stage_type', 'is_pinned']
    search_fields = ['name', 'preview_text']
