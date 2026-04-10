
"""
图片编辑阶段处理器
职责: 对多宫格切片或已有图片执行高清还原/图生图增强
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from django.utils import timezone
from jinja2 import Template, TemplateError

from apps.content.models import EditedImage, MultiGridTile, Storyboard
from apps.projects.models import Project, ProjectStage
from apps.prompts.client_param_resolver import resolve_stage_client_params
from core.ai_client.factory import create_ai_client

from .text2image_stage import Text2ImageStageProcessor

logger = logging.getLogger(__name__)


class ImageEditStageProcessor(Text2ImageStageProcessor):
    """图片编辑阶段处理器"""

    def __init__(self):
        super().__init__()
        self.stage_name = 'image_edit'
        self.stage_type = 'image_edit'

    def _get_image_edit_provider(self, project: Project):
        template = self._get_prompt_template(project)
        if template and template.model_provider:
            return template.model_provider
        return None

    def _build_prompt(self, project: Project, storyboard: dict) -> str:
        template = self._get_prompt_template(project)
        if not template:
            raise ValueError(f'未找到 {self.stage_type} 阶段的提示词模板')

        try:
            global_vars = self._get_global_variables_sync(project)
            template_vars = {
                **global_vars,
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **storyboard,
            }
            jinja_template = Template(template.template_content)
            return jinja_template.render(**template_vars)
        except TemplateError as exc:
            logger.error(f'图片编辑提示词模板渲染失败: {str(exc)}')
            raise ValueError(f'图片编辑提示词模板渲染失败: {str(exc)}')

    def _get_target_tiles(self, project: Project, storyboard_ids: Optional[List[str]] = None):
        tiles = MultiGridTile.objects.filter(
            task__storyboard__project=project,
            task__status='completed',
            status='completed',
        ).select_related('task', 'task__storyboard').order_by(
            'task__storyboard__sequence_number',
            'task__created_at',
            'tile_index',
        )
        if storyboard_ids:
            tiles = tiles.filter(task__storyboard_id__in=storyboard_ids)
        return list(tiles)

    def _resolve_edit_client_params(
        self,
        project: Project,
        provider,
        runtime_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template = self._get_prompt_template(project)
        return resolve_stage_client_params(
            self.stage_type,
            template=template,
            provider=provider,
            runtime_overrides=runtime_overrides or {},
        )

    def process_stream(
        self,
        project_id: str,
        storyboard_ids: List[str] = None,
        force_regenerate: bool = False,
        strength: float = 0.35,
        width: int = None,
        height: int = None,
    ) -> Generator[Dict[str, Any], None, None]:
        stage = None
        try:
            project = Project.objects.get(id=project_id)
            stage, _ = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)
            stage.status = 'processing'
            stage.started_at = timezone.now()
            stage.input_data = {
                **(stage.input_data or {}),
                'strength': strength,
                'width': width,
                'height': height,
            }
            stage.save()

            yield {
                'type': 'stage_update',
                'stage': {
                    'id': str(stage.id),
                    'status': 'processing',
                    'stage_type': self.stage_type,
                    'started_at': stage.started_at.isoformat(),
                }
            }

            tiles = self._get_target_tiles(project, storyboard_ids)
            if not tiles:
                yield {'type': 'error', 'error': '没有可供图片编辑的多宫格切片'}
                return

            if not force_regenerate:
                completed_tile_ids = set(
                    EditedImage.objects.filter(
                        storyboard__project=project,
                        source_stage_type='multi_grid_image',
                        status='completed',
                        multi_grid_tile_id__isnull=False,
                    ).values_list('multi_grid_tile_id', flat=True)
                )
                tiles = [tile for tile in tiles if tile.id not in completed_tile_ids]

            total = len(tiles)
            if total == 0:
                existing_results = EditedImage.objects.filter(
                    storyboard__project=project,
                    source_stage_type='multi_grid_image',
                    status='completed',
                )
                output_data = self._build_output_data(project, existing_results)
                stage.output_data = output_data
                stage.status = 'completed'
                stage.error_message = ''
                stage.completed_at = timezone.now()
                stage.save()
                yield {
                    'type': 'done',
                    'message': '图片编辑已完成，无需重复执行',
                    'data': output_data,
                    'stage': {
                        'id': str(stage.id),
                        'status': stage.status,
                        'output_data': output_data,
                        'completed_at': stage.completed_at.isoformat() if stage.completed_at else '',
                    }
                }
                return

            provider = self._get_image_edit_provider(project)
            if not provider:
                yield {'type': 'error', 'error': '未配置可用的图片编辑模型'}
                return

            client = create_ai_client(provider)
            success_count = 0
            failed_count = 0

            for index, tile in enumerate(tiles, 1):
                storyboard = tile.task.storyboard
                prompt_payload = {
                    'scene_number': storyboard.sequence_number,
                    'narration': storyboard.narration_text,
                    'visual_prompt': storyboard.image_prompt,
                    'shot_type': storyboard.scene_description,
                    'tile_index': tile.tile_index,
                    'row_index': tile.row_index,
                    'col_index': tile.col_index,
                    'tile_image_url': tile.tile_image_url,
                    'source_image_url': tile.task.source_image_url,
                    'grid_rows': tile.task.grid_rows,
                    'grid_cols': tile.task.grid_cols,
                }
                prompt = self._build_prompt(project, prompt_payload)
                client_params = self._resolve_edit_client_params(
                    project,
                    provider,
                    runtime_overrides={
                        'strength': strength,
                        'width': width or tile.width,
                        'height': height or tile.height,
                    },
                )
                output_width = client_params.get('width', tile.width or 1024)
                output_height = client_params.get('height', tile.height or 1024)

                yield {
                    'type': 'progress',
                    'current': index,
                    'total': total,
                    'message': f'正在执行第 {index}/{total} 张图片编辑...',
                }

                response = client.generate(
                    image_url=tile.tile_image_url,
                    prompt=prompt,
                    strength=client_params.get('strength', strength),
                    width=output_width,
                    height=output_height,
                    mask_url=client_params.get('mask_url', ''),
                    negative_prompt=client_params.get('negative_prompt', ''),
                )
                response_data = getattr(response, 'data', None) if not isinstance(response, dict) else response.get('data')
                response_error = getattr(response, 'error', None) if not isinstance(response, dict) else response.get('error')
                if not response_data:
                    failed_count += 1
                    logger.error('图片编辑失败: tile=%s error=%s', tile.id, response_error)
                    EditedImage.objects.update_or_create(
                        multi_grid_tile=tile,
                        defaults={
                            'storyboard': storyboard,
                            'multi_grid_task': tile.task,
                            'source_stage_type': 'multi_grid_image',
                            'source_image_url': tile.tile_image_url,
                            'edited_image_url': tile.tile_image_url,
                            'prompt_used': prompt,
                            'generation_params': {
                                'strength': client_params.get('strength', strength),
                                'tile_index': tile.tile_index,
                                'mask_url': client_params.get('mask_url', ''),
                                'negative_prompt': client_params.get('negative_prompt', ''),
                            },
                            'generation_metadata': {'error': response_error or 'empty response'},
                            'model_provider': provider,
                            'status': 'failed',
                            'width': output_width,
                            'height': output_height,
                        }
                    )
                    continue

                first_item = response_data[0] if isinstance(response_data, list) else response_data
                edited_image = EditedImage.objects.update_or_create(
                    multi_grid_tile=tile,
                    defaults={
                        'storyboard': storyboard,
                        'multi_grid_task': tile.task,
                        'source_stage_type': 'multi_grid_image',
                        'source_image_url': tile.tile_image_url,
                        'edited_image_url': first_item.get('url', ''),
                        'prompt_used': prompt,
                        'generation_params': {
                            'strength': client_params.get('strength', strength),
                            'tile_index': tile.tile_index,
                            'mask_url': client_params.get('mask_url', ''),
                            'negative_prompt': client_params.get('negative_prompt', ''),
                        },
                        'generation_metadata': {
                            **(getattr(response, 'metadata', None) or {}),
                            'tile_index': tile.tile_index,
                            'row_index': tile.row_index,
                            'col_index': tile.col_index,
                        },
                        'model_provider': provider,
                        'status': 'completed',
                        'width': first_item.get('width') or output_width,
                        'height': first_item.get('height') or output_height,
                    }
                )[0]
                success_count += 1
                yield {
                    'type': 'image_edited',
                    'sequence_number': storyboard.sequence_number,
                    'tile_index': tile.tile_index,
                    'edited_image_id': str(edited_image.id),
                }

            final_results = EditedImage.objects.filter(
                storyboard__project=project,
                source_stage_type='multi_grid_image',
            ).select_related('storyboard', 'multi_grid_task', 'multi_grid_tile', 'model_provider').order_by(
                'storyboard__sequence_number',
                'multi_grid_tile__tile_index',
            )
            output_data = self._build_output_data(project, final_results)
            stage.output_data = output_data
            stage.status = 'completed' if failed_count == 0 else 'failed'
            stage.error_message = '' if failed_count == 0 else '仍有图片编辑任务失败'
            stage.completed_at = timezone.now()
            stage.save()

            yield {
                'type': 'done',
                'message': f'图片编辑完成: 已完成 {success_count}/{total}',
                'data': output_data,
                'stage': {
                    'id': str(stage.id),
                    'status': stage.status,
                    'output_data': output_data,
                    'completed_at': stage.completed_at.isoformat() if stage.completed_at else '',
                }
            }
        except Exception as exc:
            logger.error(f'图片编辑处理失败: {str(exc)}', exc_info=True)
            if stage:
                try:
                    stage.status = 'failed'
                    stage.error_message = str(exc)
                    stage.save()
                except Exception:
                    pass
            yield {'type': 'error', 'error': str(exc)}

    def _build_output_data(self, project: Project, results):
        storyboard_map = {}
        for result in results:
            storyboard_key = str(result.storyboard_id)
            if storyboard_key not in storyboard_map:
                storyboard_map[storyboard_key] = {
                    'storyboard_id': storyboard_key,
                    'sequence_number': result.storyboard.sequence_number,
                    'results': [],
                }
            storyboard_map[storyboard_key]['results'].append({
                'id': str(result.id),
                'source_stage_type': result.source_stage_type,
                'source_image_url': result.source_image_url,
                'edited_image_url': result.edited_image_url,
                'status': result.status,
                'tile_index': result.multi_grid_tile.tile_index if result.multi_grid_tile else None,
                'row_index': result.multi_grid_tile.row_index if result.multi_grid_tile else None,
                'col_index': result.multi_grid_tile.col_index if result.multi_grid_tile else None,
                'width': result.width,
                'height': result.height,
                'model_provider': {
                    'id': str(result.model_provider.id) if result.model_provider else None,
                    'name': result.model_provider.name if result.model_provider else None,
                    'model_name': result.model_provider.model_name if result.model_provider else None,
                } if result.model_provider else None,
                'generation_params': result.generation_params,
                'generation_metadata': result.generation_metadata,
                'created_at': result.created_at.isoformat() if result.created_at else None,
            })

        return {
            'total_storyboards': Storyboard.objects.filter(project=project).count(),
            'success_count': sum(1 for result in results if result.status == 'completed'),
            'failed_count': sum(1 for result in results if result.status == 'failed'),
            'storyboards': list(storyboard_map.values()),
        }
