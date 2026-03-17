"""
多宫格图片阶段处理器
职责: 生成多宫格原图并切割成多个切片
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from django.utils import timezone

from apps.content.models import MultiGridImageTask, MultiGridTile, Storyboard
from apps.projects.models import Project, ProjectStage
from core.services.multi_grid_image_service import MultiGridImageService

from .text2image_stage import Text2ImageStageProcessor

logger = logging.getLogger(__name__)


class MultiGridImageStageProcessor(Text2ImageStageProcessor):
    """多宫格图片阶段处理器"""

    def __init__(self):
        super().__init__()
        self.stage_name = 'multi_grid_image'
        self.stage_type = 'multi_grid_image'

    def process_stream(
        self,
        project_id: str,
        storyboard_ids: List[str] = None,
        force_regenerate: bool = False,
        grid_rows: int = 2,
        grid_cols: int = 2,
        tile_gap: int = 0,
        outer_padding: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        stage = None
        try:
            project = Project.objects.get(id=project_id)
            stage, _ = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)
            stage.status = 'processing'
            stage.started_at = timezone.now()
            stage.input_data = {
                **(stage.input_data or {}),
                'grid_rows': grid_rows,
                'grid_cols': grid_cols,
                'tile_gap': tile_gap,
                'outer_padding': outer_padding,
            }
            stage.save()

            yield {
                'type': 'stage_update',
                'stage': {
                    'id': str(stage.id),
                    'status': 'processing',
                    'stage_type': self.stage_type,
                    'started_at': stage.started_at.isoformat()
                }
            }

            all_storyboards_query = Storyboard.objects.filter(project=project).order_by('sequence_number')
            target_storyboards_query = all_storyboards_query
            if storyboard_ids:
                target_storyboards_query = target_storyboards_query.filter(id__in=storyboard_ids)

            storyboards = list(target_storyboards_query)
            total = len(storyboards)
            if total == 0:
                yield {'type': 'error', 'error': '没有找到分镜数据'}
                return

            provider = self._get_text2image_provider(project)
            if not provider:
                yield {'type': 'error', 'error': '未配置可用的多宫格文生图模型'}
                return

            success_count = 0
            failed_count = 0
            storyboard_results = []

            for index, storyboard_obj in enumerate(storyboards, 1):
                storyboard_dict = {
                    'scene_number': storyboard_obj.sequence_number,
                    'narration': storyboard_obj.narration_text,
                    'visual_prompt': storyboard_obj.image_prompt,
                    'shot_type': storyboard_obj.scene_description,
                    'grid_rows': grid_rows,
                    'grid_cols': grid_cols,
                }

                yield {
                    'type': 'progress',
                    'current': index,
                    'total': total,
                    'message': f'正在生成第 {index}/{total} 张多宫格图片...',
                }

                generated_result = self._generate_single_image(project, storyboard_dict, provider)
                if not generated_result:
                    failed_count += 1
                    continue

                source_image = generated_result[0]
                split_result = MultiGridImageService.split_image(
                    image_url=source_image.get('url', ''),
                    grid_rows=grid_rows,
                    grid_cols=grid_cols,
                    tile_gap=tile_gap,
                    outer_padding=outer_padding,
                )

                task = MultiGridImageTask.objects.create(
                    storyboard=storyboard_obj,
                    source_image_url=split_result['source_image_url'],
                    grid_rows=grid_rows,
                    grid_cols=grid_cols,
                    tile_gap=tile_gap,
                    outer_padding=outer_padding,
                    split_config={
                        'source_width': split_result['source_width'],
                        'source_height': split_result['source_height'],
                    },
                    generation_params={
                        'grid_rows': grid_rows,
                        'grid_cols': grid_cols,
                    },
                    model_provider=provider,
                    status='completed',
                    prompt_used=self._build_prompt(project, storyboard_dict),
                    generation_metadata={
                        'tile_count': len(split_result['tiles']),
                    },
                )

                tile_records = []
                for tile in split_result['tiles']:
                    tile_obj = MultiGridTile.objects.create(
                        task=task,
                        tile_index=tile['tile_index'],
                        row_index=tile['row_index'],
                        col_index=tile['col_index'],
                        crop_box=tile['crop_box'],
                        tile_image_url=tile['tile_image_url'],
                        status='completed',
                        width=tile['width'],
                        height=tile['height'],
                    )
                    tile_records.append({
                        'id': str(tile_obj.id),
                        'tile_index': tile_obj.tile_index,
                        'row_index': tile_obj.row_index,
                        'col_index': tile_obj.col_index,
                        'crop_box': tile_obj.crop_box,
                        'tile_image_url': tile_obj.tile_image_url,
                        'width': tile_obj.width,
                        'height': tile_obj.height,
                        'status': tile_obj.status,
                    })

                storyboard_results.append({
                    'storyboard_id': str(storyboard_obj.id),
                    'sequence_number': storyboard_obj.sequence_number,
                    'task_id': str(task.id),
                    'status': task.status,
                    'source_image_url': task.source_image_url,
                    'grid_rows': task.grid_rows,
                    'grid_cols': task.grid_cols,
                    'tiles': tile_records,
                })
                success_count += 1

                yield {
                    'type': 'multi_grid_generated',
                    'sequence_number': storyboard_obj.sequence_number,
                }

            output_data = {
                'total_storyboards': total,
                'success_count': success_count,
                'failed_count': failed_count,
                'storyboards': storyboard_results,
            }

            stage.output_data = output_data
            stage.status = 'completed' if failed_count == 0 else 'failed'
            stage.error_message = '' if failed_count == 0 else '仍有多宫格图片生成失败'
            stage.completed_at = timezone.now()
            stage.save()

            yield {
                'type': 'done',
                'message': f'多宫格图片生成完成: 已完成 {success_count}/{total}',
                'data': output_data,
                'stage': {
                    'id': str(stage.id),
                    'status': stage.status,
                    'output_data': output_data,
                    'completed_at': stage.completed_at.isoformat() if stage.completed_at else '',
                }
            }
        except Exception as exc:
            logger.error(f'多宫格图片处理失败: {str(exc)}', exc_info=True)
            if stage:
                try:
                    stage.status = 'failed'
                    stage.error_message = str(exc)
                    stage.save()
                except Exception:
                    pass
            yield {'type': 'error', 'error': str(exc)}
