"""
内容生成领域模型
遵循单一职责原则(SRP): 每个模型只负责一种内容类型
"""

import uuid
from django.db import models
from apps.projects.models import Project
from apps.models.models import ModelProvider


class ContentRewrite(models.Model):
    """
    文案改写
    职责: 存储文案改写结果
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='content_rewrite',
        verbose_name='项目'
    )

    original_text = models.TextField('原始文本')
    rewritten_text = models.TextField('改写后文本', blank=True, default='')

    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='使用的模型'
    )

    prompt_used = models.TextField('使用的提示词', blank=True, default='')

    # 元数据
    generation_metadata = models.JSONField('生成元数据', default=dict, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'content_rewrites'
        verbose_name = '文案改写'
        verbose_name_plural = '文案改写'

    def __str__(self):
        return f'{self.project.name} - 文案改写'


class Storyboard(models.Model):
    """
    分镜
    职责: 存储分镜信息
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='storyboards',
        verbose_name='项目'
    )

    sequence_number = models.IntegerField('序号')

    scene_description = models.TextField('场景描述')
    narration_text = models.TextField('旁白文案')
    image_prompt = models.TextField('文生图提示词')

    duration_seconds = models.FloatField('时长(秒)', default=3.0)

    # 新增: 生成元数据
    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='使用的模型'
    )
    prompt_used = models.TextField('使用的提示词', blank=True, default='')
    generation_metadata = models.JSONField('生成元数据', default=dict, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'storyboards'
        verbose_name = '分镜'
        verbose_name_plural = '分镜'
        unique_together = [('project', 'sequence_number')]
        ordering = ['sequence_number']
        indexes = [
            models.Index(fields=['project', 'sequence_number']),
        ]

    def __str__(self):
        return f'{self.project.name} - 分镜{self.sequence_number}'


class GeneratedImage(models.Model):
    """
    生成图片
    职责: 存储生成的图片信息
    """

    STATUS_CHOICES = [
        ('pending', '待生成'),
        ('processing', '生成中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storyboard = models.ForeignKey(
        Storyboard,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='分镜'
    )

    image_url = models.URLField('图片URL', max_length=1024)
    thumbnail_url = models.URLField('缩略图URL', max_length=1024, blank=True)

    # 生成参数
    generation_params = models.JSONField('生成参数', default=dict)

    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='使用的模型'
    )

    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField('重试次数', default=0)

    # 文件信息
    file_size = models.BigIntegerField('文件大小(字节)', default=0)
    width = models.IntegerField('宽度', default=0)
    height = models.IntegerField('高度', default=0)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'generated_images'
        verbose_name = '生成图片'
        verbose_name_plural = '生成图片'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['storyboard', 'status']),
        ]

    def __str__(self):
        return f'{self.storyboard} - 图片'


class CameraMovement(models.Model):
    """
    运镜
    职责: 存储运镜参数
    """

    MOVEMENT_TYPES = [
        ('static', '静态'),
        ('zoom_in', '推进'),
        ('zoom_out', '拉远'),
        ('pan_left', '左移'),
        ('pan_right', '右移'),
        ('tilt_up', '上摇'),
        ('tilt_down', '下摇'),
        ('dolly_in', '前推'),
        ('dolly_out', '后拉'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storyboard = models.OneToOneField(
        Storyboard,
        on_delete=models.CASCADE,
        related_name='camera_movement',
        verbose_name='分镜'
    )

    movement_type = models.CharField('运镜类型', max_length=50, choices=MOVEMENT_TYPES, blank=True, default='')
    movement_params = models.JSONField('运镜参数', default=dict, blank=True)

    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='使用的模型'
    )

    prompt_used = models.TextField('使用的提示词', blank=True, default='')
    generation_metadata = models.JSONField('生成元数据', default=dict, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'camera_movements'
        verbose_name = '运镜'
        verbose_name_plural = '运镜'

    def __str__(self):
        return f'{self.storyboard} - {self.get_movement_type_display() if self.movement_type else "未设置"}'


class GeneratedVideo(models.Model):
    """
    生成视频
    职责: 存储生成的视频信息
    """

    STATUS_CHOICES = [
        ('pending', '待生成'),
        ('processing', '生成中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storyboard = models.ForeignKey(
        Storyboard,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='分镜'
    )

    image = models.ForeignKey(
        GeneratedImage,
        on_delete=models.CASCADE,
        verbose_name='源图片'
    )

    camera_movement = models.ForeignKey(
        CameraMovement,
        on_delete=models.CASCADE,
        verbose_name='运镜'
    )

    video_url = models.URLField('视频URL', max_length=1024)
    thumbnail_url = models.URLField('缩略图URL', max_length=1024, blank=True)

    # 视频属性
    duration = models.FloatField('时长(秒)', default=0)
    width = models.IntegerField('宽度', default=0)
    height = models.IntegerField('高度', default=0)
    fps = models.IntegerField('帧率', default=24)
    file_size = models.BigIntegerField('文件大小(字节)', default=0)

    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='使用的模型'
    )

    generation_params = models.JSONField('生成参数', default=dict)

    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField('重试次数', default=0)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'generated_videos'
        verbose_name = '生成视频'
        verbose_name_plural = '生成视频'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['storyboard', 'status']),
        ]

    def __str__(self):
        return f'{self.storyboard} - 视频'



class MultiGridImageTask(models.Model):
    """
    多宫格图片任务
    职责: 存储多宫格图片生成与切片任务
    """

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storyboard = models.ForeignKey(
        Storyboard,
        on_delete=models.CASCADE,
        related_name='multi_grid_tasks',
        verbose_name='分镜'
    )
    source_image_url = models.URLField('多宫格原图URL', max_length=1024)
    grid_rows = models.IntegerField('行数', default=2)
    grid_cols = models.IntegerField('列数', default=2)
    tile_gap = models.IntegerField('格子间距', default=0)
    outer_padding = models.IntegerField('外边距', default=0)
    split_config = models.JSONField('切图配置', default=dict, blank=True)
    generation_params = models.JSONField('生成参数', default=dict, blank=True)
    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='使用的模型'
    )
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    prompt_used = models.TextField('使用的提示词', blank=True, default='')
    generation_metadata = models.JSONField('生成元数据', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'multi_grid_image_tasks'
        verbose_name = '多宫格图片任务'
        verbose_name_plural = '多宫格图片任务'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['storyboard', 'status']),
        ]

    def __str__(self):
        return f'{self.storyboard} - 多宫格任务'


class MultiGridTile(models.Model):
    """
    多宫格切片
    职责: 存储多宫格切分后的单图结果
    """

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        MultiGridImageTask,
        on_delete=models.CASCADE,
        related_name='tiles',
        verbose_name='多宫格任务'
    )
    tile_index = models.IntegerField('切片序号')
    row_index = models.IntegerField('行序号')
    col_index = models.IntegerField('列序号')
    crop_box = models.JSONField('裁切区域', default=dict, blank=True)
    tile_image_url = models.URLField('切片图片URL', max_length=1024)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='completed')
    width = models.IntegerField('宽度', default=0)
    height = models.IntegerField('高度', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'multi_grid_tiles'
        verbose_name = '多宫格切片'
        verbose_name_plural = '多宫格切片'
        ordering = ['tile_index']
        unique_together = [('task', 'tile_index')]
        indexes = [
            models.Index(fields=['task', 'tile_index']),
        ]

    def __str__(self):
        return f'{self.task} - 切片{self.tile_index}'



class EditedImage(models.Model):
    """
    图片编辑结果
    职责: 存储图片编辑/高清还原后的图片结果
    """

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    SOURCE_STAGE_CHOICES = [
        ('image_generation', '文生图'),
        ('multi_grid_image', '多宫格图片'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storyboard = models.ForeignKey(
        Storyboard,
        on_delete=models.CASCADE,
        related_name='edited_images',
        verbose_name='分镜'
    )
    multi_grid_task = models.ForeignKey(
        MultiGridImageTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_images',
        verbose_name='来源多宫格任务'
    )
    multi_grid_tile = models.ForeignKey(
        MultiGridTile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_images',
        verbose_name='来源多宫格切片'
    )
    source_stage_type = models.CharField('来源阶段', max_length=20, choices=SOURCE_STAGE_CHOICES, default='multi_grid_image')
    source_image_url = models.URLField('源图片URL', max_length=1024)
    edited_image_url = models.URLField('编辑后图片URL', max_length=1024)
    prompt_used = models.TextField('使用的提示词', blank=True, default='')
    generation_params = models.JSONField('生成参数', default=dict, blank=True)
    generation_metadata = models.JSONField('生成元数据', default=dict, blank=True)
    model_provider = models.ForeignKey(
        ModelProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='使用的模型'
    )
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='completed')
    retry_count = models.IntegerField('重试次数', default=0)
    width = models.IntegerField('宽度', default=0)
    height = models.IntegerField('高度', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'edited_images'
        verbose_name = '图片编辑结果'
        verbose_name_plural = '图片编辑结果'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['storyboard', 'status']),
            models.Index(fields=['multi_grid_tile']),
        ]

    def __str__(self):
        return f'{self.storyboard} - 图片编辑结果'
