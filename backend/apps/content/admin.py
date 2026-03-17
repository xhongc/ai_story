"""内容生成Admin配置"""
from django.contrib import admin
from .models import (
    ContentRewrite,
    Storyboard,
    GeneratedImage,
    CameraMovement,
    GeneratedVideo,
    MultiGridImageTask,
    MultiGridTile,
    EditedImage,
)


@admin.register(ContentRewrite)
class ContentRewriteAdmin(admin.ModelAdmin):
    list_display = ['project', 'model_provider', 'created_at']
    search_fields = ['original_text', 'rewritten_text']


@admin.register(Storyboard)
class StoryboardAdmin(admin.ModelAdmin):
    list_display = ['project', 'sequence_number', 'duration_seconds', 'created_at']
    list_filter = ['created_at']
    ordering = ['project', 'sequence_number']


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'status', 'width', 'height', 'created_at']
    list_filter = ['status', 'created_at']


@admin.register(CameraMovement)
class CameraMovementAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'movement_type', 'model_provider', 'created_at']
    list_filter = ['movement_type']


@admin.register(GeneratedVideo)
class GeneratedVideoAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'status', 'duration', 'width', 'height', 'created_at']
    list_filter = ['status', 'created_at']



@admin.register(MultiGridImageTask)
class MultiGridImageTaskAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'status', 'grid_rows', 'grid_cols', 'created_at']
    list_filter = ['status', 'created_at']


@admin.register(MultiGridTile)
class MultiGridTileAdmin(admin.ModelAdmin):
    list_display = ['task', 'tile_index', 'row_index', 'col_index', 'created_at']
    list_filter = ['created_at']



@admin.register(EditedImage)
class EditedImageAdmin(admin.ModelAdmin):
    list_display = ['storyboard', 'source_stage_type', 'status', 'width', 'height', 'created_at']
    list_filter = ['source_stage_type', 'status', 'created_at']
