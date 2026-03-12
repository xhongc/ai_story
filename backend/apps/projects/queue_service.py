"""分集任务队列服务。"""

import logging
from typing import Any, Dict, Optional

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import EpisodeTaskQueue, Project, Series

logger = logging.getLogger(__name__)

ACTIVE_QUEUE_STATUSES = ['waiting', 'running']


def _project_task_cache_key(project_id: str) -> str:
    return f"project_active_tasks:{project_id}"


def _register_project_task(project_id: str, task_id: str) -> None:
    task_ids = cache.get(_project_task_cache_key(project_id), [])
    if task_id not in task_ids:
        task_ids.append(task_id)
    cache.set(_project_task_cache_key(project_id), task_ids, timeout=24 * 60 * 60)


def _get_queue_position(queue_task: EpisodeTaskQueue) -> int:
    return (
        EpisodeTaskQueue.objects.filter(
            series_id=queue_task.series_id,
            status__in=ACTIVE_QUEUE_STATUSES,
            created_at__lt=queue_task.created_at,
        ).count() + 1
    )


def get_active_queue_task_for_project(project: Project) -> Optional[EpisodeTaskQueue]:
    return (
        EpisodeTaskQueue.objects.filter(
            project=project,
            status__in=ACTIVE_QUEUE_STATUSES,
        )
        .order_by('created_at')
        .first()
    )


def enqueue_episode_task(
    project: Project,
    created_by,
    task_type: str,
    payload: Optional[Dict[str, Any]] = None,
    stage_name: str = '',
) -> Dict[str, Any]:
    """将分集任务加入队列，并尝试立即调度。"""
    if not project.series_id:
        raise ValueError('仅系列分集支持排队')

    with transaction.atomic():
        Series.objects.select_for_update().get(id=project.series_id)

        existing_task = (
            EpisodeTaskQueue.objects.select_for_update()
            .filter(project=project, status__in=ACTIVE_QUEUE_STATUSES)
            .order_by('created_at')
            .first()
        )
        if existing_task:
            queue_task = existing_task
        else:
            queue_task = EpisodeTaskQueue.objects.create(
                series_id=project.series_id,
                project=project,
                task_type=task_type,
                stage_name=stage_name,
                payload=payload or {},
                created_by=created_by,
                status='waiting',
            )
            if project.status != 'processing':
                project.status = 'queued'
                project.completed_at = None
                project.save(update_fields=['status', 'completed_at', 'updated_at'])

    dispatch_next_episode_task(project.series_id)
    queue_task.refresh_from_db()

    return {
        'queue_task': queue_task,
        'queue_position': _get_queue_position(queue_task),
        'started': queue_task.status == 'running',
        'already_exists': existing_task is not None,
    }


def _launch_queue_task(queue_task_id: str) -> EpisodeTaskQueue:
    from apps.projects.tasks import (
        execute_image2video_stage,
        execute_llm_stage,
        execute_text2image_stage,
        run_full_pipeline_task,
    )

    queue_task = EpisodeTaskQueue.objects.select_related('project', 'created_by').get(id=queue_task_id)
    if queue_task.celery_task_id:
        return queue_task

    payload = queue_task.payload or {}
    project = queue_task.project

    if queue_task.task_type == 'pipeline':
        task = run_full_pipeline_task.delay(
            project_id=str(project.id),
            user_id=queue_task.created_by_id,
        )
    elif queue_task.task_type == 'stage':
        stage_name = queue_task.stage_name
        if stage_name in ['rewrite', 'storyboard', 'camera_movement']:
            task = execute_llm_stage.delay(
                project_id=str(project.id),
                stage_name=stage_name,
                input_data=payload,
                user_id=queue_task.created_by_id,
            )
        elif stage_name == 'image_generation':
            task = execute_text2image_stage.delay(
                project_id=str(project.id),
                storyboard_ids=payload.get('storyboard_ids'),
                user_id=queue_task.created_by_id,
            )
        elif stage_name == 'video_generation':
            task = execute_image2video_stage.delay(
                project_id=str(project.id),
                storyboard_ids=payload.get('storyboard_ids'),
                user_id=queue_task.created_by_id,
            )
        else:
            raise ValueError(f'未知阶段类型: {stage_name}')
    else:
        raise ValueError(f'未知任务类型: {queue_task.task_type}')

    queue_task.celery_task_id = task.id
    queue_task.save(update_fields=['celery_task_id', 'updated_at'])
    _register_project_task(str(project.id), task.id)
    return queue_task


def dispatch_next_episode_task(series_id: str) -> Optional[EpisodeTaskQueue]:
    """调度同一作品下等待中的下一个分集任务。"""
    with transaction.atomic():
        Series.objects.select_for_update().get(id=series_id)

        running_task = (
            EpisodeTaskQueue.objects.select_for_update()
            .filter(series_id=series_id, status='running')
            .order_by('created_at')
            .first()
        )
        if running_task:
            return running_task

        queue_task = (
            EpisodeTaskQueue.objects.select_for_update()
            .select_related('project')
            .filter(series_id=series_id, status='waiting')
            .order_by('created_at')
            .first()
        )
        if not queue_task:
            return None

        queue_task.status = 'running'
        queue_task.started_at = timezone.now()
        queue_task.save(update_fields=['status', 'started_at', 'updated_at'])

        Project.objects.filter(id=queue_task.project_id).update(
            status='processing',
            completed_at=None,
        )

    try:
        return _launch_queue_task(str(queue_task.id))
    except Exception:
        logger.exception('启动队列任务失败: %s', queue_task.id)
        complete_episode_task_by_celery_id('', 'failed', queue_task_id=queue_task.id)
        return None


def complete_episode_task_by_celery_id(
    celery_task_id: str,
    final_status: str,
    queue_task_id: Optional[str] = None,
) -> Optional[EpisodeTaskQueue]:
    """根据 Celery 任务 ID 完成队列任务，并调度下一个。"""
    with transaction.atomic():
        queue_tasks = EpisodeTaskQueue.objects.select_for_update().filter(status='running')
        if queue_task_id:
            queue_task = queue_tasks.filter(id=queue_task_id).first()
        else:
            queue_task = queue_tasks.filter(celery_task_id=celery_task_id).first()

        if not queue_task:
            return None

        queue_task.status = final_status
        queue_task.completed_at = timezone.now()
        queue_task.save(update_fields=['status', 'completed_at', 'updated_at'])
        series_id = queue_task.series_id

    dispatch_next_episode_task(series_id)
    return queue_task


def cancel_running_queue_task(project: Project) -> Optional[EpisodeTaskQueue]:
    """取消项目当前运行中的队列任务。"""
    if not project.series_id:
        return None

    with transaction.atomic():
        queue_task = (
            EpisodeTaskQueue.objects.select_for_update()
            .filter(project=project, status='running')
            .order_by('created_at')
            .first()
        )
        if not queue_task:
            return None

        queue_task.status = 'cancelled'
        queue_task.completed_at = timezone.now()
        queue_task.save(update_fields=['status', 'completed_at', 'updated_at'])
        series_id = queue_task.series_id

    dispatch_next_episode_task(series_id)
    return queue_task
