"""提示词管理Admin配置"""
from django.contrib import admin
from .models import PromptTemplateSet, PromptTemplate, GlobalVariable


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
