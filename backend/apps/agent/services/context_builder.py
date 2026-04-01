from apps.projects.models import Project


STAGE_LABEL_MAP = {
    'rewrite': '改写',
    'asset_extraction': '资产提取',
    'storyboard': '分镜',
    'image_generation': '图片生成',
    'multi_grid_image': '多图生成',
    'image_edit': '图片编辑',
    'camera_movement': '运镜',
    'video_generation': '视频生成',
}


def get_stage_label(stage_type):
    return STAGE_LABEL_MAP.get(stage_type, stage_type or '未知阶段')


class AgentContextBuilder:
    def build(self, *, user, scope_key, route_name='', route_params=None, ui_context=None):
        route_params = route_params or {}
        ui_context = ui_context or {}

        if scope_key.startswith('project_detail:') or route_name == 'ProjectDetail':
            project_id = route_params.get('id') or scope_key.split(':', 1)[-1]
            return self._build_project_detail(user=user, project_id=project_id, ui_context=ui_context)

        return {
            'page_type': 'generic',
            'title': route_name or '当前页面',
            'summary': '当前页面暂未接入专用业务上下文，我可以先基于页面结构提供导航和下一步建议。',
            'ui_context': ui_context,
        }

    def _build_project_detail(self, *, user, project_id, ui_context=None):
        project = Project.objects.filter(id=project_id, user=user).prefetch_related('stages').select_related('series').first()
        if not project:
            return {
                'page_type': 'project_detail',
                'title': '分集详情',
                'summary': '未找到当前项目，可能已被删除或你没有访问权限。',
                'ui_context': ui_context or {},
                'entities': {
                    'project_id': project_id,
                },
            }

        stages = list(project.stages.all())
        completed_count = len([stage for stage in stages if stage.status == 'completed'])
        failed_stages = [stage for stage in stages if stage.status == 'failed']
        processing_stage = next((stage for stage in stages if stage.status == 'processing'), None)
        storyboard_stage = next((stage for stage in stages if stage.stage_type == 'storyboard'), None)
        storyboards = (storyboard_stage.domain_data or {}).get('storyboards', []) if storyboard_stage else []
        camera_storyboard = next((item for item in storyboards if item.get('camera_movement', {}).get('data', {}).get('id')), None)

        if processing_stage:
            summary = f'当前正在执行 {get_stage_label(processing_stage.stage_type)} 阶段。'
        elif failed_stages:
            summary = f'{get_stage_label(failed_stages[0].stage_type)} 阶段存在失败记录，建议优先定位。'
        elif project.status == 'completed':
            summary = '当前项目流程已完成，可以回看并微调内容。'
        elif project.status == 'paused':
            summary = '当前项目已暂停，可继续恢复流程或局部调整。'
        else:
            summary = '当前项目处于可编辑状态，可以继续执行或微调。'

        return {
            'page_type': 'project_detail',
            'title': project.display_name or project.name or '分集详情',
            'summary': summary,
            'stats': {
                'total_stages': len(stages),
                'completed_stages': completed_count,
                'failed_stages': len(failed_stages),
                'storyboard_count': len(storyboards),
                'camera_ready_count': len([item for item in storyboards if item.get('camera_movement', {}).get('data', {}).get('id')]),
            },
            'entities': {
                'project_id': str(project.id),
                'project_status': project.status,
                'processing_stage': processing_stage.stage_type if processing_stage else '',
                'failed_stage': failed_stages[0].stage_type if failed_stages else '',
                'first_storyboard_id': storyboards[0].get('id') if storyboards else None,
                'first_camera_storyboard_id': camera_storyboard.get('id') if camera_storyboard else None,
                'first_camera_id': (camera_storyboard.get('camera_movement', {}).get('data', {}) or {}).get('id') if camera_storyboard else None,
            },
            'ui_context': ui_context or {},
        }
