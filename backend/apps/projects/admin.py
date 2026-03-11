"""项目管理Admin配置"""
from django.contrib import admin
from .models import Project, ProjectStage, ProjectModelConfig, ProjectAssetBinding


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'user', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    list_display = ['project', 'stage_type', 'status', 'retry_count', 'created_at']
    list_filter = ['stage_type', 'status']


@admin.register(ProjectModelConfig)
class ProjectModelConfigAdmin(admin.ModelAdmin):
    list_display = ['project', 'load_balance_strategy', 'created_at']


@admin.register(ProjectAssetBinding)
class ProjectAssetBindingAdmin(admin.ModelAdmin):
    list_display = ['project', 'asset', 'created_at']
    list_filter = ['created_at']
    search_fields = ['project__name', 'asset__key']
