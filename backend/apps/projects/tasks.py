"""
项目相关的Celery异步任务
职责: 执行耗时的AI生成任务，通过Redis Pub/Sub推送实时进度
遵循单一职责原则(SRP)
"""

import logging
from typing import Dict, Any
from celery.exceptions import TaskRevokedError
from django.core.cache import cache
from django.utils import timezone

from core.redis import RedisStreamPublisher
from core.services.jianying_draft_service import JianyingDraftGenerator
from apps.content.models import GeneratedImage, Storyboard
from apps.content.processors.llm_stage import LLMStageProcessor
from apps.content.processors.text2image_stage import Text2ImageStageProcessor
from apps.content.processors.image2video_stage import Image2VideoStageProcessor
from apps.projects.models import Project, ProjectStage
from apps.projects.utils import is_stage_template_enabled
from config.celery_app import app

logger = logging.getLogger(__name__)


def _skip_stage(stage: ProjectStage, message: str) -> None:
    """将阶段标记为跳过。"""
    now = timezone.now()
    stage.status = 'skipped'
    stage.started_at = now
    stage.completed_at = now
    stage.error_message = message
    stage.save(update_fields=['status', 'started_at', 'completed_at', 'error_message'])


def _project_task_cache_key(project_id: str) -> str:
    return f"project_active_tasks:{project_id}"


def _unregister_project_task(project_id: str, task_id: str) -> None:
    task_ids = cache.get(_project_task_cache_key(project_id), [])
    if not task_ids:
        return

    remaining_task_ids = [current_task_id for current_task_id in task_ids if current_task_id != task_id]
    if remaining_task_ids:
        cache.set(_project_task_cache_key(project_id), remaining_task_ids, timeout=24 * 60 * 60)
    else:
        cache.delete(_project_task_cache_key(project_id))


def _get_missing_image_storyboard_ids(project: Project, storyboard_ids=None):
    """返回仍未生成完成图片的分镜ID列表。"""
    storyboards_query = Storyboard.objects.filter(project=project).order_by('sequence_number')

    if storyboard_ids is not None:
        storyboards_query = storyboards_query.filter(id__in=storyboard_ids)

    completed_storyboard_ids = set(
        GeneratedImage.objects.filter(
            storyboard__project=project,
            status='completed'
        ).values_list('storyboard_id', flat=True).distinct()
    )

    return [str(storyboard.id) for storyboard in storyboards_query if storyboard.id not in completed_storyboard_ids]


def _is_image_generation_complete(project: Project) -> bool:
    """按实际图片产出判断文生图阶段是否真正完成。"""
    total_storyboards = Storyboard.objects.filter(project=project).count()
    if total_storyboards == 0:
        return False

    completed_storyboards = GeneratedImage.objects.filter(
        storyboard__project=project,
        status='completed'
    ).values('storyboard_id').distinct().count()

    return completed_storyboards >= total_storyboards


def _mark_stage_paused(project_id: str, stage_name: str) -> None:
    ProjectStage.objects.filter(
        project_id=project_id,
        stage_type=stage_name,
        status='processing'
    ).update(
        status='pending',
        completed_at=None,
        error_message=''
    )


def _is_project_paused(project_id: str) -> bool:
    return Project.objects.filter(id=project_id, status='paused').exists()


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=600,  # 10分钟软超时
    time_limit=900  # 15分钟硬超时
)
def execute_llm_stage(
    self,
    project_id: str,
    stage_name: str,
    input_data: Dict[str, Any],
    user_id: int
) -> Dict[str, Any]:
    """
    执行LLM阶段任务 (文案改写/分镜生成/运镜生成)

    Args:
        self: Celery任务实例
        project_id: 项目ID
        stage_name: 阶段名称 (rewrite/storyboard/camera_movement)
        input_data: 输入数据
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """

    task_id = self.request.id
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行LLM阶段任务: {stage_name}, 项目: {project_id}, 任务ID: {task_id}")

    # 初始化Redis发布器
    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id, user_id=user_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        if not is_stage_template_enabled(project, stage_name):
            message = f'{stage.get_stage_type_display()} 对应提示词模板未开启，已跳过该阶段'
            _skip_stage(stage, message)
            publisher.publish_stage_update(status='skipped', progress=100, message=message)
            publisher.publish_stage_completed({'stage_type': stage_name, 'status': 'skipped'})
            return {
                'success': True,
                'task_id': task_id,
                'channel': channel,
                'skipped': True,
                'message': message,
            }

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message=f'开始执行{stage.get_stage_type_display()}'
        )

        # 创建处理器
        processor = LLMStageProcessor(stage_type=stage_name)

        # 执行流式处理
        full_text = ""

        for chunk in processor.process_stream(
            project_id=project_id,
            input_data=input_data
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'token':
                # 发布token消息
                content = chunk.get('content', '')
                full_text = chunk.get('full_text', full_text)
                publisher.publish_token(content, full_text)

            elif chunk_type == 'camera_generated':
                # 单个运镜生成完成，通知前端刷新
                publisher.publish_item_completed(
                    item_type='camera',
                    sequence_number=chunk.get('sequence_number', 0),
                    metadata={'sequence_number': chunk.get('sequence_number', 0)}
                )

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                full_text = chunk.get('full_text', full_text)
                metadata = chunk.get('metadata', {})

                # 更新阶段状态
                ProjectStage.objects.filter(id=stage.id).update(
                    completed_at=timezone.now(),
                    status='completed'
                )
                # 发布完成消息
                publisher.publish_done(full_text, metadata)
                # 发布阶段完成消息 (通知前端刷新画布)
                publisher.publish_stage_completed(metadata)

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        logger.info(f"LLM阶段任务完成: {stage_name}, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel,
            'result': full_text
        }

    except Project.DoesNotExist:
        error_msg = f'项目不存在: {project_id}'
        logger.error(error_msg)
        publisher.publish_error(error_msg)
        return {'success': False, 'error': error_msg}

    except ProjectStage.DoesNotExist:
        error_msg = f'阶段不存在: {stage_name}'
        logger.error(error_msg)
        publisher.publish_error(error_msg)
        return {'success': False, 'error': error_msg}

    except TaskRevokedError:
        logger.info(f"LLM阶段任务已撤销: {stage_name}, 项目: {project_id}, 任务ID: {task_id}")
        _mark_stage_paused(project_id, stage_name)
        return {'success': False, 'paused': True, 'error': '任务已暂停'}

    except Exception as e:
        if _is_project_paused(project_id):
            logger.info(f"LLM阶段任务因项目暂停中断: {stage_name}, 项目: {project_id}, 任务ID: {task_id}")
            _mark_stage_paused(project_id, stage_name)
            return {'success': False, 'paused': True, 'error': '任务已暂停'}

        error_msg = f'任务执行失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            logger.info(f"任务将在60秒后重试 (第{self.request.retries + 1}次)")
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        _unregister_project_task(project_id, task_id)
        publisher.close()


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=600,
    time_limit=900
)
def execute_text2image_stage(
    self,
    project_id: str,
    storyboard_ids: list = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    执行文生图阶段任务

    Args:
        self: Celery任务实例
        project_id: 项目ID
        storyboard_ids: 分镜ID列表 (可选，为空则处理所有分镜)
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """
    task_id = self.request.id
    stage_name = 'image_generation'
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行文生图任务, 项目: {project_id}, 任务ID: {task_id}")

    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        if not is_stage_template_enabled(project, stage_name):
            message = '文生图提示词模板未开启，已跳过该阶段'
            _skip_stage(stage, message)
            publisher.publish_stage_update(status='skipped', progress=100, message=message)
            publisher.publish_stage_completed({'stage_type': stage_name, 'status': 'skipped'})
            return {
                'success': True,
                'task_id': task_id,
                'channel': channel,
                'skipped': True,
                'message': message,
            }

        pending_storyboard_ids = _get_missing_image_storyboard_ids(project, storyboard_ids)

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message='开始生成图片'
        )

        # 创建处理器
        processor = Text2ImageStageProcessor()

        # 执行流式处理
        for chunk in processor.process_stream(
            project_id=project_id,
            storyboard_ids=pending_storyboard_ids if storyboard_ids is not None else None
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'progress':
                # 发布进度消息
                publisher.publish_progress(
                    current=chunk.get('current', 0),
                    total=chunk.get('total', 0),
                    item_name=chunk.get('item_name', ''),
                )

            elif chunk_type == 'image_generated':
                # 单个图片生成完成，通知前端刷新
                publisher.publish_item_completed(
                    item_type='image',
                    sequence_number=chunk.get('sequence_number', 0),
                    metadata={'sequence_number': chunk.get('sequence_number', 0)}
                )

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                result_data = chunk.get('data', {})
                stage_data = chunk.get('stage', {})
                stage_status = stage_data.get('status', 'completed')
                error_message = '' if stage_status == 'completed' else chunk.get('message', '文生图阶段未完成')

                # 更新阶段状态
                ProjectStage.objects.filter(id=stage.id).update(
                    status=stage_status,
                    output_data=result_data,
                    completed_at=timezone.now(),
                    error_message=error_message,
                )

                if stage_status == 'completed':
                    publisher.publish_done(metadata=result_data)
                    publisher.publish_stage_completed(result_data)
                else:
                    publisher.publish_stage_update(
                        status=stage_status,
                        progress=100,
                        message=error_message
                    )

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        stage.refresh_from_db()

        if stage.status != 'completed':
            logger.warning(f"文生图任务未完全完成, 项目: {project_id}, 状态: {stage.status}")
            return {
                'success': False,
                'task_id': task_id,
                'channel': channel,
                'error': stage.error_message or '文生图阶段未完成'
            }

        logger.info(f"文生图任务完成, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel
        }

    except TaskRevokedError:
        logger.info(f"文生图任务已撤销, 项目: {project_id}, 任务ID: {task_id}")
        _mark_stage_paused(project_id, stage_name)
        return {'success': False, 'paused': True, 'error': '任务已暂停'}

    except Exception as e:
        if _is_project_paused(project_id):
            logger.info(f"文生图任务因项目暂停中断, 项目: {project_id}, 任务ID: {task_id}")
            _mark_stage_paused(project_id, stage_name)
            return {'success': False, 'paused': True, 'error': '任务已暂停'}

        error_msg = f'文生图任务失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        _unregister_project_task(project_id, task_id)
        publisher.close()


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=1200,  # 20分钟软超时 (视频生成较慢)
    time_limit=1500  # 25分钟硬超时
)
def execute_image2video_stage(
    self,
    project_id: str,
    storyboard_ids: list = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    执行图生视频阶段任务

    Args:
        self: Celery任务实例
        project_id: 项目ID
        storyboard_ids: 分镜ID列表 (可选，为空则处理所有分镜)
        user_id: 用户ID

    Returns:
        Dict包含: success, task_id, channel, result
    """
    task_id = self.request.id
    stage_name = 'video_generation'
    channel = f"ai_story:project:{project_id}:stage:{stage_name}"

    logger.info(f"开始执行图生视频任务, 项目: {project_id}, 任务ID: {task_id}")

    publisher = RedisStreamPublisher(project_id, stage_name)

    try:
        # 获取项目和阶段
        project = Project.objects.get(id=project_id)
        stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

        if not is_stage_template_enabled(project, stage_name):
            message = '图生视频提示词模板未开启，已跳过该阶段'
            _skip_stage(stage, message)
            publisher.publish_stage_update(status='skipped', progress=100, message=message)
            publisher.publish_stage_completed({'stage_type': stage_name, 'status': 'skipped'})
            return {
                'success': True,
                'task_id': task_id,
                'channel': channel,
                'skipped': True,
                'message': message,
            }

        # 更新阶段状态
        stage.status = 'processing'
        stage.started_at = timezone.now()
        stage.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message='开始生成视频'
        )

        # 创建处理器
        processor = Image2VideoStageProcessor()

        # 执行流式处理
        for chunk in processor.process_stream(
            project_id=project_id,
            storyboard_ids=storyboard_ids
        ):
            chunk_type = chunk.get('type')

            if chunk_type == 'progress':
                # 发布进度消息
                publisher.publish_progress(
                    current=chunk.get('current', 0),
                    total=chunk.get('total', 0),
                    item_name=chunk.get('item_name', '')
                )

            elif chunk_type == 'video_generated':
                # 单个视频生成完成，通知前端刷新
                publisher.publish_item_completed(
                    item_type='video',
                    sequence_number=chunk.get('scene_number', 0),
                    metadata={'scene_number': chunk.get('scene_number', 0)}
                )

            elif chunk_type == 'stage_update':
                # 发布阶段更新
                publisher.publish_stage_update(
                    status=chunk.get('status', 'processing'),
                    progress=chunk.get('progress'),
                    message=chunk.get('message')
                )

            elif chunk_type == 'done':
                # 处理完成
                metadata = chunk.get('metadata', {})
                # 发布完成消息
                publisher.publish_done(metadata=metadata)
                # 发布阶段完成消息 (通知前端刷新画布)
                publisher.publish_stage_completed(metadata)

            elif chunk_type == 'error':
                # 处理错误
                error_msg = chunk.get('error', '未知错误')
                raise Exception(error_msg)

        logger.info(f"图生视频任务完成, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel
        }

    except TaskRevokedError:
        logger.info(f"图生视频任务已撤销, 项目: {project_id}, 任务ID: {task_id}")
        _mark_stage_paused(project_id, stage_name)
        return {'success': False, 'paused': True, 'error': '任务已暂停'}

    except Exception as e:
        if _is_project_paused(project_id):
            logger.info(f"图生视频任务因项目暂停中断, 项目: {project_id}, 任务ID: {task_id}")
            _mark_stage_paused(project_id, stage_name)
            return {'success': False, 'paused': True, 'error': '任务已暂停'}

        error_msg = f'图生视频任务失败: {str(e)}'
        logger.exception(error_msg)

        # 更新阶段状态
        try:
            stage = ProjectStage.objects.get(
                project_id=project_id,
                stage_type=stage_name
            )
            stage.status = 'failed'
            stage.error_message = error_msg
            stage.retry_count += 1
            stage.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg, retry_count=self.request.retries)

        # 重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        _unregister_project_task(project_id, task_id)
        publisher.close()


@app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=300,  # 5分钟软超时
    time_limit=600  # 10分钟硬超时
)
def generate_jianying_draft(
    self,
    project_id: str,
    user_id: int = None,
    background_music: str = None,
    **options
) -> Dict[str, Any]:
    """
    生成剪映草稿任务

    Args:
        self: Celery任务实例
        project_id: 项目ID
        user_id: 用户ID
        background_music: 背景音乐文件路径（可选）
        **options: 其他可选参数
            - draft_folder_path: 草稿保存路径
            - music_volume: 背景音乐音量
            - add_intro_animation: 是否添加入场动画
            等等...

    Returns:
        Dict包含: success, draft_path, error
    """
    task_id = self.request.id
    channel = f"ai_story:project:{project_id}:jianying_draft"

    logger.info(f"开始生成剪映草稿, 项目: {project_id}, 任务ID: {task_id}")


    try:
        # 获取项目
        project = Project.objects.get(id=project_id)
        # 检查视频生成阶段是否完成
        video_stage = ProjectStage.objects.filter(
            project=project,
            stage_type='video_generation',
            status='completed'
        ).first()

        if not video_stage:
            raise ValueError('视频生成阶段未完成，无法生成剪映草稿')

        # 获取场景数据
        scenes = video_stage.output_data.get('human_text', {}).get('scenes', [])

        if not scenes:
            raise ValueError('没有找到视频场景数据')

        # 过滤出有视频的场景
        valid_scenes = [s for s in scenes if s.get('video_urls')]

        if not valid_scenes:
            raise ValueError('没有找到已生成的视频')

        logger.info(f"找到 {len(valid_scenes)} 个有效视频场景")


        # 创建剪映草稿生成器
        draft_folder_path = options.pop('draft_folder_path', None)
        generator = JianyingDraftGenerator(draft_folder_path=draft_folder_path)

        # 生成草稿
        draft_path = generator.generate_from_project_data(
            project_name=f"{project.name}_{project.id}",
            scenes=valid_scenes,
            background_music=background_music,
            **options
        )

        logger.info(f"剪映草稿生成成功: {draft_path}")

        # 更新项目的剪映草稿路径
        project.jianying_draft_path = draft_path
        project.save(update_fields=['jianying_draft_path'])


        return {
            'success': True,
            'task_id': task_id,
            'channel': channel,
            'draft_path': draft_path
        }

    except Project.DoesNotExist:
        error_msg = f'项目不存在: {project_id}'
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

    except ValueError as e:
        error_msg = str(e)
        logger.error(f'参数错误: {error_msg}')
        return {'success': False, 'error': error_msg}

    except Exception as e:
        error_msg = f'生成剪映草稿失败: {str(e)}'
        logger.exception(error_msg)

        # 发布错误消息

        # 重试
        if self.request.retries < self.max_retries:
            logger.info(f"任务将在60秒后重试 (第{self.request.retries + 1}次)")
            raise self.retry(exc=e, countdown=60)

        return {'success': False, 'error': error_msg}

    finally:
        pass


@app.task(
    bind=True,
    max_retries=0,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=3600,  # 60分钟软超时（完整流程较长）
    time_limit=4200  # 70分钟硬超时
)
def run_full_pipeline_task(
    self,
    project_id: str,
    user_id: int
) -> Dict[str, Any]:
    """
    运行完整工作流任务（智能跳过已完成阶段）

    Args:
        self: Celery任务实例
        project_id: 项目ID
        user_id: 用户ID

    Returns:
        Dict包含: success, completed_stages, skipped_stages, error
    """
    task_id = self.request.id
    channel = f"ai_story:project:{project_id}:pipeline"

    logger.info(f"开始运行完整工作流, 项目: {project_id}, 任务ID: {task_id}")

    # 初始化Redis发布器
    publisher = RedisStreamPublisher(project_id, 'pipeline')

    # 定义阶段顺序
    stage_order = [
        'rewrite',
        'storyboard',
        'image_generation',
        'camera_movement',
        'video_generation'
    ]

    completed_stages = []
    skipped_stages = []

    try:
        # 获取项目
        project = Project.objects.get(id=project_id, user_id=user_id)

        # 更新项目状态
        project.status = 'processing'
        project.save()

        # 发布开始消息
        publisher.publish_stage_update(
            status='processing',
            progress=0,
            message='开始执行完整工作流'
        )

        # 遍历所有阶段
        for index, stage_name in enumerate(stage_order):
            try:
                # 获取阶段
                stage = ProjectStage.objects.get(project=project, stage_type=stage_name)

                if not is_stage_template_enabled(project, stage_name):
                    message = f'阶段 {stage.get_stage_type_display()} 的提示词模板未开启，自动跳过'
                    logger.info(message)
                    _skip_stage(stage, message)
                    skipped_stages.append(stage_name)
                    publisher.publish_stage_update(
                        status='skipped',
                        progress=int((index + 1) / len(stage_order) * 100),
                        message=message
                    )
                    continue

                # 检查阶段是否已完成
                if stage.status == 'completed':
                    if stage_name == 'image_generation' and not _is_image_generation_complete(project):
                        logger.warning(f"阶段 {stage_name} 状态异常，检测到仍有未生成图片，自动继续补跑")
                        stage.status = 'failed'
                        stage.error_message = '检测到仍有分镜图片未生成完成，自动继续补跑'
                        stage.save(update_fields=['status', 'error_message'])
                    else:
                        logger.info(f"阶段 {stage_name} 已完成，跳过")
                        skipped_stages.append(stage_name)

                        # 发布跳过消息
                        publisher.publish_stage_update(
                            status='processing',
                            progress=int((index + 1) / len(stage_order) * 100),
                            message=f'阶段 {stage.get_stage_type_display()} 已完成，跳过'
                        )
                        continue

                # 执行阶段
                logger.info(f"开始执行阶段: {stage_name}")

                # 发布阶段开始消息
                publisher.publish_stage_update(
                    status='processing',
                    progress=int(index / len(stage_order) * 100),
                    message=f'开始执行阶段: {stage.get_stage_type_display()}'
                )

                # 根据阶段类型调用对应的任务
                if stage_name in ['rewrite', 'storyboard', 'camera_movement']:
                    # LLM类阶段
                    input_data = stage.input_data or {}
                    result = execute_llm_stage(
                        project_id=project_id,
                        stage_name=stage_name,
                        input_data=input_data,
                        user_id=user_id
                    )

                elif stage_name == 'image_generation':
                    # 文生图阶段
                    result = execute_text2image_stage(
                        project_id=project_id,
                        storyboard_ids=None,  # 处理所有分镜
                        user_id=user_id
                    )

                elif stage_name == 'video_generation':
                    # 图生视频阶段
                    result = execute_image2video_stage(
                        project_id=project_id,
                        storyboard_ids=None,  # 处理所有分镜
                        user_id=user_id
                    )

                # 检查执行结果
                if result.get('paused'):
                    logger.info(f"阶段 {stage_name} 因项目暂停中断")
                    return {
                        'success': False,
                        'paused': True,
                        'task_id': task_id,
                        'channel': channel,
                        'completed_stages': completed_stages,
                        'skipped_stages': skipped_stages
                    }
                if result.get('success'):
                    completed_stages.append(stage_name)
                    logger.info(f"阶段 {stage_name} 执行成功")
                else:
                    error_msg = result.get('error', '未知错误')
                    raise Exception(f"阶段 {stage_name} 执行失败: {error_msg}")

            except ProjectStage.DoesNotExist:
                error_msg = f'阶段不存在: {stage_name}'
                logger.error(error_msg)
                raise Exception(error_msg)

        # 所有阶段完成
        project.status = 'completed'
        project.save()

        # 发布完成消息
        publisher.publish_done(
            metadata={
                'completed_stages': completed_stages,
                'skipped_stages': skipped_stages,
                'total_stages': len(stage_order)
            }
        )

        # 发布流程完成消息 (用于全阶段订阅的结束信号)
        publisher.publish_pipeline_done(
            metadata={
                'completed_stages': completed_stages,
                'skipped_stages': skipped_stages,
                'total_stages': len(stage_order)
            }
        )

        logger.info(f"完整工作流执行完成, 项目: {project_id}")

        return {
            'success': True,
            'task_id': task_id,
            'channel': channel,
            'completed_stages': completed_stages,
            'skipped_stages': skipped_stages
        }

    except Project.DoesNotExist:
        error_msg = f'项目不存在: {project_id}'
        logger.error(error_msg)
        publisher.publish_error(error_msg)
        return {'success': False, 'error': error_msg}

    except TaskRevokedError:
        logger.info(f"完整工作流任务已撤销, 项目: {project_id}, 任务ID: {task_id}")
        return {
            'success': False,
            'paused': True,
            'task_id': task_id,
            'channel': channel,
            'completed_stages': completed_stages,
            'skipped_stages': skipped_stages
        }

    except Exception as e:
        if _is_project_paused(project_id):
            logger.info(f"完整工作流因项目暂停结束, 项目: {project_id}, 任务ID: {task_id}")
            return {
                'success': False,
                'paused': True,
                'task_id': task_id,
                'channel': channel,
                'completed_stages': completed_stages,
                'skipped_stages': skipped_stages
            }

        error_msg = f'工作流执行失败: {str(e)}'
        logger.exception(error_msg)

        # 更新项目状态
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'failed'
            project.save()
        except Exception:
            pass

        # 发布错误消息
        publisher.publish_error(error_msg)

        # 发布流程错误消息 (用于全阶段订阅的结束信号)
        publisher.publish_pipeline_error(error_msg)

        return {'success': False, 'error': error_msg}

    finally:
        _unregister_project_task(project_id, task_id)
        publisher.close()
