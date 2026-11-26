import uuid
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from types import SimpleNamespace
from unittest.mock import patch

from core.ai_client.base import AIResponse

from apps.content.models import ContentRewrite, GeneratedImage, Storyboard
from apps.projects.models import Project, ProjectStage, Series
from apps.workflows.node_schema_runtime import prepare_node_run_input_payload
from apps.workflows.node_executors.execute_image_generation import execute_image_generation
from apps.workflows.node_executors.execute_rewrite import execute_rewrite
from apps.workflows.node_executors.execute_video_generation import execute_video_generation
from apps.workflows.node_executors.lifecycle import finalize_success
from apps.workflows.models import (
    WorkflowCallbackEvent,
    WorkflowCanvas,
    WorkflowEdge,
    WorkflowNode,
    WorkflowNodeRun,
    WorkflowNodeRunEvent,
    WorkflowNodeSchema,
    WorkflowRun,
)


User = get_user_model()


def initialize_project(project):
    for stage_type in ['rewrite', 'asset_extraction', 'storyboard', 'image_generation', 'multi_grid_image', 'camera_movement', 'video_generation', 'image_edit']:
        ProjectStage.objects.create(project=project, stage_type=stage_type, status='pending')
    ContentRewrite.objects.create(project=project, original_text=project.original_topic)


class WorkflowCanvasPermissionAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='canvas-owner', password='secret123')
        self.other_user = User.objects.create_user(username='canvas-other', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='本人作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='本人文案',
        )
        self.other_series = Series.objects.create(name='其他作品', description='desc', user=self.other_user)
        self.other_project = Project.objects.create(
            user=self.other_user,
            series=self.other_series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='其他文案',
        )
        self.canvas = WorkflowCanvas.objects.create(
            name='本人画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.other_canvas = WorkflowCanvas.objects.create(
            name='其他用户画板',
            project=self.other_project,
            series=self.other_series,
            created_by=self.other_user,
            status='active',
        )
        self.cross_project_canvas = WorkflowCanvas.objects.create(
            name='跨项目历史脏数据',
            project=self.other_project,
            series=self.other_series,
            created_by=self.user,
            status='active',
        )
        self.missing_creator_canvas = WorkflowCanvas.objects.create(
            name='缺少创建人的历史数据',
            project=self.project,
            series=self.series,
            created_by=None,
            status='active',
        )

    def test_canvas_list_only_returns_current_user_items(self):
        response = self.client.get(reverse('workflow-canvas-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get('results', response.data)
        canvas_ids = {str(item['id']) for item in items}
        self.assertIn(str(self.canvas.id), canvas_ids)
        self.assertNotIn(str(self.other_canvas.id), canvas_ids)
        self.assertNotIn(str(self.cross_project_canvas.id), canvas_ids)
        self.assertNotIn(str(self.missing_creator_canvas.id), canvas_ids)

    def test_canvas_detail_rejects_other_user_item(self):
        response = self.client.get(reverse('workflow-canvas-detail', args=[self.other_canvas.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_canvas_detail_rejects_cross_project_item(self):
        response = self.client.get(reverse('workflow-canvas-detail', args=[self.cross_project_canvas.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_canvas_create_rejects_other_user_project(self):
        response = self.client.post(
            reverse('workflow-canvas-list'),
            {
                'name': '跨用户画板',
                'project': str(self.other_project.id),
                'series': str(self.other_series.id),
                'status': 'draft',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(WorkflowCanvas.objects.filter(name='跨用户画板').count(), 0)


class WorkflowCallbackAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='workflow-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='测试作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        self.canvas = WorkflowCanvas.objects.create(
            name='测试画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.rewrite_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='rewrite_node',
            node_type='rewrite',
            title='改写',
            status='completed',
        )
        self.storyboard_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='storyboard_node',
            node_type='storyboard',
            title='分镜',
            status='completed',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='edge-1',
            source_node=self.rewrite_node,
            target_node=self.storyboard_node,
        )
        self.node_run = WorkflowNodeRun.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.rewrite_node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='waiting_callback',
            external_task_id='ext-task-1',
        )

    def test_callback_is_idempotent_and_updates_rewrite(self):
        url = reverse('workflow-callback-list')
        payload = {
            'workflow_run_id': str(self.workflow_run.id),
            'node_run_id': str(self.node_run.id),
            'provider': 'linknow',
            'event_type': 'task.completed',
            'idempotency_key': 'callback-1',
            'external_task_id': 'ext-task-1',
            'status': 'completed',
            'payload': {'rewritten_text': '改写结果'},
            'normalized_output': {'rewritten_text': '改写结果'},
            'auto_apply': True,
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WorkflowCallbackEvent.objects.count(), 1)

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WorkflowCallbackEvent.objects.count(), 1)

        self.node_run.refresh_from_db()
        self.assertEqual(self.node_run.status, 'completed')
        rewrite = ContentRewrite.objects.get(project=self.project)
        self.assertEqual(rewrite.rewritten_text, '改写结果')


class WorkflowNodeApplyAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apply-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='测试作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        self.canvas = WorkflowCanvas.objects.create(
            name='应用画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.storyboard_node_model = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='storyboard_node',
            node_type='storyboard',
            title='分镜',
        )
        self.image_node_model = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='image_node',
            node_type='image_generation',
            title='图片',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='edge-storyboard-image',
            source_node=self.storyboard_node_model,
            target_node=self.image_node_model,
        )

    def test_apply_storyboard_then_images(self):
        storyboard_node = WorkflowNodeRun.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.storyboard_node_model,
            node_key='storyboard_node',
            node_type='storyboard',
            normalized_output={
                'storyboards': [
                    {
                        'sequence_number': 1,
                        'scene_description': '场景1',
                        'narration_text': '旁白1',
                        'image_prompt': '提示词1',
                        'duration_seconds': 3,
                    }
                ]
            },
        )

        response = self.client.post(reverse('workflow-node-run-apply', args=[storyboard_node.id]), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        storyboard = Storyboard.objects.get(project=self.project, sequence_number=1)
        self.assertEqual(storyboard.scene_description, '场景1')

        image_node = WorkflowNodeRun.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.image_node_model,
            node_key='image_node',
            node_type='image_generation',
            normalized_output={
                'storyboards': [
                    {
                        'sequence_number': 1,
                        'images': [
                            {
                                'external_task_id': 'img-task-1',
                                'image_url': 'https://example.com/1.png',
                                'status': 'completed',
                                'width': 1280,
                                'height': 720,
                            }
                        ],
                    }
                ]
            },
        )

        response = self.client.post(reverse('workflow-node-run-apply', args=[image_node.id]), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        images = GeneratedImage.objects.filter(storyboard=storyboard)
        self.assertEqual(images.count(), 1)
        self.assertEqual(images.first().image_url, 'https://example.com/1.png')

    def test_apply_asset_extraction_stage_output(self):
        asset_run = WorkflowNodeRun.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.storyboard_node_model,
            node_key='asset_node',
            node_type='asset_extraction',
            normalized_output={
                'source_text': '故事文本',
                'source_type': 'manual',
                'summary': '抽取到角色和场景',
                'items': [
                    {
                        'temp_id': 'item_1',
                        'key': 'hero',
                        'label': '主角',
                        'group': '角色',
                        'variable_type': 'image',
                        'value': '',
                        'confidence': 0.9,
                        'match_status': 'unmatched',
                        'candidates': [],
                        'selected_asset_id': None,
                        'selected_action': None,
                    }
                ],
            },
        )

        response = self.client.post(reverse('workflow-node-run-apply', args=[asset_run.id]), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stage = ProjectStage.objects.get(project=self.project, stage_type='asset_extraction')
        self.assertEqual(stage.output_data['summary'], '抽取到角色和场景')
        self.assertEqual(len(stage.output_data['items']), 1)
        self.assertEqual(stage.output_data['items'][0]['key'], 'hero')


class WorkflowInvalidationAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='invalidate-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='测试作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.canvas = WorkflowCanvas.objects.create(
            name='失效画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.node_a = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='node_a',
            node_type='rewrite',
            title='A',
            status='completed',
            config_data={'prompt': 'v1'},
        )
        self.node_b = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='node_b',
            node_type='storyboard',
            title='B',
            status='completed',
        )
        self.node_c = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='node_c',
            node_type='image_generation',
            title='C',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='edge-a-b',
            source_node=self.node_a,
            target_node=self.node_b,
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='edge-b-c',
            source_node=self.node_b,
            target_node=self.node_c,
        )

    def test_graph_update_marks_downstream_nodes_stale_or_dirty(self):
        response = self.client.patch(
            reverse('workflow-canvas-graph', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'id': str(self.node_a.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_a',
                        'node_type': 'rewrite',
                        'title': 'A',
                        'status': 'completed',
                        'position_x': 0,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {'prompt': 'v2'},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.node_b.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_b',
                        'node_type': 'storyboard',
                        'title': 'B',
                        'status': 'completed',
                        'position_x': 0,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.node_c.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_c',
                        'node_type': 'image_generation',
                        'title': 'C',
                        'status': 'idle',
                        'position_x': 0,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                ],
                'edges': [
                    {
                        'id': str(self.canvas.edges.get(edge_key='edge-a-b').id),
                        'canvas': str(self.canvas.id),
                        'edge_key': 'edge-a-b',
                        'source_node': str(self.node_a.id),
                        'target_node': str(self.node_b.id),
                        'source_handle': '',
                        'target_handle': '',
                        'metadata': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.canvas.edges.get(edge_key='edge-b-c').id),
                        'canvas': str(self.canvas.id),
                        'edge_key': 'edge-b-c',
                        'source_node': str(self.node_b.id),
                        'target_node': str(self.node_c.id),
                        'source_handle': '',
                        'target_handle': '',
                        'metadata': {},
                        'is_enabled': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.node_b.refresh_from_db()
        self.node_c.refresh_from_db()
        self.assertEqual(self.node_b.status, 'stale')
        self.assertEqual(self.node_c.status, 'dirty')

    def test_graph_update_can_persist_new_split_child_nodes_without_edges(self):
        new_child_id = uuid.uuid4()

        response = self.client.patch(
            reverse('workflow-canvas-graph', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'id': str(self.node_a.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_a',
                        'node_type': 'rewrite',
                        'title': 'A',
                        'status': 'completed',
                        'position_x': 0,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {'prompt': 'v1'},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.node_b.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_b',
                        'node_type': 'storyboard',
                        'title': 'B',
                        'status': 'completed',
                        'position_x': 320,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.node_c.id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'node_c',
                        'node_type': 'image_generation',
                        'title': 'C',
                        'status': 'idle',
                        'position_x': 640,
                        'position_y': 0,
                        'width': 320,
                        'height': 180,
                        'config_data': {},
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(new_child_id),
                        'canvas': str(self.canvas.id),
                        'node_key': 'text:split-child',
                        'node_type': 'rewrite',
                        'title': 'Split Child',
                        'status': 'dirty',
                        'position_x': 840,
                        'position_y': 120,
                        'width': 400,
                        'height': 250,
                        'config_data': {
                            'label': '分镜 1',
                            'type': 'text',
                            'text': 'child prompt',
                            'prompt': '',
                        },
                        'input_mapping': {},
                        'output_schema': {},
                        'latest_output': {
                            'text': 'child prompt',
                            'rewritten_text': 'child prompt',
                            'prompt': '',
                            'model': '',
                            'multiplier': '1x',
                        },
                        'is_enabled': True,
                    },
                ],
                'edges': [
                    {
                        'id': str(self.canvas.edges.get(edge_key='edge-a-b').id),
                        'canvas': str(self.canvas.id),
                        'edge_key': 'edge-a-b',
                        'source_node': str(self.node_a.id),
                        'target_node': str(self.node_b.id),
                        'source_handle': '',
                        'target_handle': '',
                        'metadata': {},
                        'is_enabled': True,
                    },
                    {
                        'id': str(self.canvas.edges.get(edge_key='edge-b-c').id),
                        'canvas': str(self.canvas.id),
                        'edge_key': 'edge-b-c',
                        'source_node': str(self.node_b.id),
                        'target_node': str(self.node_c.id),
                        'source_handle': '',
                        'target_handle': '',
                        'metadata': {},
                        'is_enabled': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            WorkflowNode.objects.filter(
                canvas=self.canvas,
                id=new_child_id,
                node_key='text:split-child',
            ).exists()
        )

    def test_callback_completion_marks_downstream_nodes_stale_or_dirty(self):
        node_run = WorkflowNodeRun.objects.create(
            canvas=self.canvas,
            node=self.node_a,
            node_key='node_a',
            node_type='rewrite',
            status='waiting_callback',
            external_task_id='node-a-task',
        )
        response = self.client.post(
            reverse('workflow-callback-list'),
            {
                'canvas_id': str(self.canvas.id),
                'node_run_id': str(node_run.id),
                'provider': 'linknow',
                'event_type': 'task.completed',
                'idempotency_key': 'node-a-callback',
                'external_task_id': 'node-a-task',
                'status': 'completed',
                'payload': {'rewritten_text': '改写完成'},
                'normalized_output': {'rewritten_text': '改写完成'},
                'auto_apply': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.node_a.refresh_from_db()
        self.node_b.refresh_from_db()
        self.node_c.refresh_from_db()
        self.assertEqual(self.node_a.status, 'completed')
        self.assertEqual(self.node_b.status, 'stale')
        self.assertEqual(self.node_c.status, 'dirty')


class WorkflowNodeExecutionAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='execute-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='测试作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.canvas = WorkflowCanvas.objects.create(
            name='执行画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='rewrite_node',
            node_type='rewrite',
            title='改写',
            status='idle',
        )

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_enqueues_celery_task(self, mock_delay):
        mock_delay.return_value.id = 'celery-node-task-1'

        response = self.client.post(
            reverse('workflow-node-execute', args=[self.node.id]),
            {
                'input_payload': {
                    'original_text': '原文',
                    'instruction': '改成更口语化',
                    'model': 'test-model',
                },
                'trigger_source': 'manual',
                'idempotency_key': 'node-run-1',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'queued')
        self.assertEqual(response.data['external_task_id'], 'celery-node-task-1')
        self.node.refresh_from_db()
        self.assertEqual(self.node.status, 'queued')
        node_run = WorkflowNodeRun.objects.get(id=response.data['id'])
        self.assertEqual(node_run.status, 'queued')
        self.assertEqual(node_run.external_task_id, 'celery-node-task-1')
        mock_delay.assert_called_once_with(str(node_run.id))

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_allows_missing_original_text(self, mock_delay):
        mock_delay.return_value.id = 'celery-node-task-no-original'

        response = self.client.post(
            reverse('workflow-node-execute', args=[self.node.id]),
            {
                'input_payload': {
                    'instruction': '直接给出改写建议',
                    'model': 'test-model',
                },
                'trigger_source': 'manual',
                'idempotency_key': 'node-run-no-original',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'queued')
        node_run = WorkflowNodeRun.objects.get(id=response.data['id'])
        self.assertEqual(node_run.input_payload.get('instruction'), '直接给出改写建议')
        self.assertNotIn('original_text', node_run.input_payload)
        mock_delay.assert_called_once_with(str(node_run.id))

    @patch('apps.workflows.views.AsyncResult')
    def test_stream_returns_terminal_event(self, mock_async_result):
        node_run = WorkflowNodeRun.objects.create(
            canvas=self.canvas,
            node=self.node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='completed',
            external_task_id='celery-node-task-2',
            normalized_output={'rewritten_text': '已完成'},
            output_payload={'choices': []},
        )
        mock_async_result.return_value.state = 'SUCCESS'

        response = self.client.get(reverse('workflow-node-run-stream', args=[node_run.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chunks = list(response.streaming_content)
        payload_text = b''.join(chunks).decode('utf-8')
        self.assertIn('"type": "connected"', payload_text)
        self.assertIn('"type": "done"', payload_text)
        self.assertIn('"status": "completed"', payload_text)

    @patch('apps.workflows.views.AsyncResult')
    def test_stream_accepts_text_event_stream_header(self, mock_async_result):
        node_run = WorkflowNodeRun.objects.create(
            canvas=self.canvas,
            node=self.node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='completed',
            external_task_id='celery-node-task-3',
            normalized_output={'rewritten_text': '已完成'},
        )
        mock_async_result.return_value.state = 'SUCCESS'

        response = self.client.get(
            reverse('workflow-node-run-stream', args=[node_run.id]),
            HTTP_ACCEPT='text/event-stream',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_selection_enqueues_multiple_nodes(self, mock_delay):
        second_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='storyboard_node',
            node_type='storyboard',
            title='分镜',
            status='idle',
        )
        mock_delay.side_effect = [
            SimpleNamespace(id='celery-node-task-11'),
            SimpleNamespace(id='celery-node-task-12'),
        ]

        response = self.client.post(
            reverse('workflow-canvas-execute-selection', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'node_id': str(self.node.id),
                        'input_payload': {
                            'original_text': '原文',
                            'instruction': '改成更口语化',
                            'model': 'test-model',
                        },
                        'trigger_source': 'manual',
                        'idempotency_key': 'node-run-batch-1',
                    },
                    {
                        'node_id': str(second_node.id),
                        'input_payload': {
                            'raw_text': '故事文本',
                            'text': '故事文本',
                            'model': 'story-model',
                            'prompt_template_id': 'template-1',
                        },
                        'trigger_source': 'manual',
                        'idempotency_key': 'node-run-batch-2',
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['summary']['total_count'], 2)
        self.assertEqual(response.data['summary']['queued_count'], 2)
        self.assertEqual(response.data['summary']['failed_count'], 0)
        self.assertEqual(response.data['summary']['pending_count'], 0)
        self.assertEqual(len(response.data['runs']), 2)
        self.assertEqual({item['status'] for item in response.data['runs']}, {'queued'})
        self.assertEqual(mock_delay.call_count, 2)
        self.node.refresh_from_db()
        second_node.refresh_from_db()
        self.assertEqual(self.node.status, 'queued')
        self.assertEqual(second_node.status, 'queued')

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_selection_accepts_single_node_batch(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-node-task-single')

        response = self.client.post(
            reverse('workflow-canvas-execute-selection', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'node_id': str(self.node.id),
                        'input_payload': {
                            'original_text': '原文',
                            'instruction': '改成更口语化',
                            'model': 'test-model',
                        },
                        'trigger_source': 'manual',
                        'idempotency_key': 'node-run-single-batch',
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['summary']['total_count'], 1)
        self.assertEqual(response.data['summary']['queued_count'], 1)
        self.assertEqual(response.data['summary']['failed_count'], 0)
        self.assertEqual(response.data['summary']['pending_count'], 0)
        self.assertEqual(len(response.data['runs']), 1)
        self.assertEqual(response.data['runs'][0]['status'], 'queued')
        mock_delay.assert_called_once()

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_selection_accepts_asset_extraction_node(self, mock_delay):
        asset_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='asset_node',
            node_type='asset_extraction',
            title='资产抽取',
            status='idle',
        )
        mock_delay.return_value = SimpleNamespace(id='celery-node-task-asset')

        response = self.client.post(
            reverse('workflow-canvas-execute-selection', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'node_id': str(asset_node.id),
                        'input_payload': {
                            'raw_text': '故事文本',
                            'text': '故事文本',
                            'model': 'asset-model',
                            'prompt_template_id': 'template-asset-1',
                        },
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['summary']['queued_count'], 1)
        self.assertEqual(response.data['summary']['pending_count'], 0)
        asset_node.refresh_from_db()
        self.assertEqual(asset_node.status, 'queued')
        mock_delay.assert_called_once()

    @patch('apps.workflows.views.execute_workflow_node_task.delay')
    def test_execute_selection_accepts_dependent_nodes_in_dag_order(self, mock_delay):
        second_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='image_node',
            node_type='image_generation',
            title='图片',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='rewrite-to-image',
            source_node=self.node,
            target_node=second_node,
        )

        response = self.client.post(
            reverse('workflow-canvas-execute-selection', args=[self.canvas.id]),
            {
                'nodes': [
                    {
                        'node_id': str(self.node.id),
                        'input_payload': {'original_text': '原文', 'instruction': '改写', 'model': 'test-model'},
                    },
                    {
                        'node_id': str(second_node.id),
                        'input_payload': {'prompt': '补充要求', 'model': 'image-model'},
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['summary']['total_count'], 2)
        self.assertEqual(response.data['summary']['queued_count'], 1)
        self.assertEqual(response.data['summary']['pending_count'], 1)
        self.assertEqual(response.data['summary']['failed_count'], 0)
        statuses = {item['node_key']: item['status'] for item in response.data['runs']}
        self.assertEqual(statuses['rewrite_node'], 'queued')
        self.assertEqual(statuses['image_node'], 'pending')
        mock_delay.assert_called_once()
        self.node.refresh_from_db()
        second_node.refresh_from_db()
        self.assertEqual(self.node.status, 'queued')
        self.assertEqual(second_node.status, 'idle')


class ExecuteRewriteNodeExecutorTestCase(APITestCase):
    @patch('apps.workflows.node_executors.execute_rewrite.requests.post')
    @patch('apps.workflows.node_executors.execute_rewrite._pick_provider')
    def test_execute_rewrite_allows_missing_original_text(self, mock_pick_provider, mock_post):
        mock_pick_provider.return_value = SimpleNamespace(
            model_name='provider-model',
            timeout=30,
            max_tokens=1024,
            api_key='secret',
            api_url='https://example.com/v1/chat/completions',
        )
        mock_post.return_value = SimpleNamespace(
            status_code=200,
            json=lambda: {
                'choices': [
                    {
                        'message': {
                            'content': '这是改写建议',
                        },
                    },
                ],
            },
        )

        result = execute_rewrite({
            'instruction': '直接给出改写建议',
            'model': 'rewrite-model',
        })

        self.assertEqual(result['normalized_output']['rewritten_text'], '这是改写建议')
        self.assertEqual(result['normalized_output']['original_text'], '')
        request_payload = mock_post.call_args.kwargs['json']
        user_message = request_payload['messages'][1]['content']
        self.assertIn('修改要求：\n直接给出改写建议', user_message)
        self.assertNotIn('原始内容：', user_message)

    @patch('apps.workflows.node_executors.execute_rewrite.requests.post')
    @patch('apps.workflows.node_executors.execute_rewrite._pick_provider')
    def test_execute_rewrite_uses_node_schema_system_prompt(self, mock_pick_provider, mock_post):
        mock_pick_provider.return_value = SimpleNamespace(
            model_name='provider-model',
            timeout=30,
            max_tokens=1024,
            api_key='secret',
            api_url='https://example.com/v1/chat/completions',
        )
        mock_post.return_value = SimpleNamespace(
            status_code=200,
            json=lambda: {
                'choices': [
                    {
                        'message': {
                            'content': '改写结果',
                        },
                    },
                ],
            },
        )

        execute_rewrite({
            'instruction': '改写',
            '__node_schema': {
                'system_prompt': '你是{{ role }}',
            },
            'role': '短剧编辑',
        })

        request_payload = mock_post.call_args.kwargs['json']
        self.assertEqual(request_payload['messages'][0]['content'], '你是短剧编辑')


class WorkflowImageInputRuntimeTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='image-input-user', password='secret123')
        self.series = Series.objects.create(name='图片输入作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.canvas = WorkflowCanvas.objects.create(
            name='图片输入画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )

    def test_prepare_payload_adds_completed_upstream_image_output(self):
        workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        image_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='image_node',
            node_type='image_generation',
            title='图片',
            status='completed',
        )
        video_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='video_node',
            node_type='video_generation',
            title='视频',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='image-to-video',
            source_node=image_node,
            target_node=video_node,
        )
        WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=image_node,
            node_key='image_node',
            node_type='image_generation',
            status='completed',
            normalized_output={
                'image_url': '/api/v1/content/storage/image/2026-06-05/upstream.png',
            },
        )
        video_run = WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=video_node,
            node_key='video_node',
            node_type='video_generation',
            status='pending',
            input_payload={'prompt': '生成视频', 'model': 'video-model'},
        )

        payload = prepare_node_run_input_payload(video_run)

        self.assertEqual(payload['image_url'], '/api/v1/content/storage/image/2026-06-05/upstream.png')
        self.assertEqual(payload['image_urls'], ['/api/v1/content/storage/image/2026-06-05/upstream.png'])

    def test_prepare_video_generation_payload_prefers_upstream_online_url(self):
        workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        image_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='image_node',
            node_type='image_generation',
            title='图片',
            status='completed',
        )
        video_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='video_node',
            node_type='video_generation',
            title='视频',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='image-to-video',
            source_node=image_node,
            target_node=video_node,
        )
        WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=image_node,
            node_key='image_node',
            node_type='image_generation',
            status='completed',
            normalized_output={
                'image_url': '/api/v1/content/storage/image/2026-06-05/local.png',
            },
            output_payload={
                'data': [
                    {
                        'url': '/api/v1/content/storage/image/2026-06-05/local.png',
                        'original_url': 'https://cdn.example.com/original.png',
                    }
                ],
            },
        )
        video_run = WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=video_node,
            node_key='video_node',
            node_type='video_generation',
            status='pending',
            input_payload={'prompt': '生成视频', 'model': 'video-model'},
        )

        payload = prepare_node_run_input_payload(video_run)

        self.assertEqual(payload['image_url'], 'https://cdn.example.com/original.png')
        self.assertEqual(payload['image_urls'], ['https://cdn.example.com/original.png'])

    def test_prepare_video_generation_payload_uses_upstream_text_as_prompt(self):
        workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        rewrite_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='rewrite_node',
            node_type='rewrite',
            title='文本',
            status='completed',
        )
        video_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='video_node',
            node_type='video_generation',
            title='视频',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='rewrite-to-video',
            source_node=rewrite_node,
            target_node=video_node,
        )
        WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=rewrite_node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='completed',
            normalized_output={
                'rewritten_text': '上游文本节点输出的提示词',
                'prompt': '这条不应优先于 rewritten_text',
            },
        )
        video_run = WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=video_node,
            node_key='video_node',
            node_type='video_generation',
            status='pending',
            input_payload={'prompt': '', 'model': 'video-model'},
        )

        payload = prepare_node_run_input_payload(video_run)

        self.assertEqual(payload['prompt'], '上游文本节点输出的提示词')
        self.assertEqual(payload['text'], '上游文本节点输出的提示词')

    def test_prepare_video_generation_payload_keeps_explicit_prompt(self):
        workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        rewrite_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='rewrite_node',
            node_type='rewrite',
            title='文本',
            status='completed',
        )
        video_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='video_node',
            node_type='video_generation',
            title='视频',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='rewrite-to-video-keep',
            source_node=rewrite_node,
            target_node=video_node,
        )
        WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=rewrite_node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='completed',
            normalized_output={
                'rewritten_text': '上游文本节点输出的提示词',
            },
        )
        video_run = WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=video_node,
            node_key='video_node',
            node_type='video_generation',
            status='pending',
            input_payload={'prompt': '手动填写的视频提示词', 'model': 'video-model'},
        )

        payload = prepare_node_run_input_payload(video_run)

        self.assertEqual(payload['prompt'], '手动填写的视频提示词')
        self.assertNotIn('text', payload)

    def test_prepare_image_generation_payload_prefers_upstream_online_url(self):
        workflow_run = WorkflowRun.objects.create(project=self.project, series=self.series, created_by=self.user)
        source_image_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='source_image_node',
            node_type='image_generation',
            title='上游图片',
            status='completed',
        )
        target_image_node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='target_image_node',
            node_type='image_generation',
            title='下游图片',
            status='idle',
        )
        WorkflowEdge.objects.create(
            canvas=self.canvas,
            edge_key='image-to-image',
            source_node=source_image_node,
            target_node=target_image_node,
        )
        WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=source_image_node,
            node_key='source_image_node',
            node_type='image_generation',
            status='completed',
            normalized_output={
                'image_url': '/api/v1/content/storage/image/2026-06-05/local.png',
            },
            output_payload={
                'data': [
                    {
                        'url': '/api/v1/content/storage/image/2026-06-05/local.png',
                        'original_url': 'https://cdn.example.com/original.png',
                    }
                ],
            },
        )
        target_run = WorkflowNodeRun.objects.create(
            workflow_run=workflow_run,
            canvas=self.canvas,
            node=target_image_node,
            node_key='target_image_node',
            node_type='image_generation',
            status='pending',
            input_payload={'prompt': '生成图片', 'model': 'image-model'},
        )

        payload = prepare_node_run_input_payload(target_run)

        self.assertEqual(payload['source_image_url'], 'https://cdn.example.com/original.png')
        self.assertEqual(payload['source_images'], ['https://cdn.example.com/original.png'])

    @patch('apps.workflows.node_executors.execute_image_generation.create_ai_client_for_user')
    @patch('apps.workflows.node_executors.execute_image_generation.ImageGenerationService.edit')
    @patch('apps.workflows.node_executors.execute_image_generation._pick_provider')
    def test_image_generation_converts_storage_reference_to_data_url(self, mock_pick_provider, mock_edit, mock_create_client):
        with tempfile.TemporaryDirectory() as storage_root:
            image_path = Path(storage_root) / 'image' / '2026-06-05' / 'source.png'
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(b'\x89PNG\r\n\x1a\nlocal-image')

            mock_pick_provider.return_value = SimpleNamespace(
                id=uuid.uuid4(),
                name='Image Edit Provider',
                provider_type='image_edit',
                get_provider_type_display=lambda: '图片编辑',
                model_name='image-edit-model',
                api_url='https://example.com/v1/images/edits',
                api_key='secret',
            )
            mock_create_client.return_value = SimpleNamespace()
            mock_edit.return_value = AIResponse(
                success=True,
                data=[{'url': '/api/v1/content/storage/image/2026-06-05/generated.png'}],
            )

            with override_settings(STORAGE_ROOT=Path(storage_root)):
                result = execute_image_generation({
                    'prompt': '基于参考图生成',
                    'model': 'image-edit-model',
                    'mode': 'img2img',
                    'source_image_url': '/api/v1/content/storage/image/2026-06-05/source.png',
                })

        request = mock_edit.call_args.args[1]
        self.assertTrue(request.source_images[0].startswith('data:image/png;base64,'))
        self.assertEqual(
            result['normalized_output']['source_image_url'],
            '/api/v1/content/storage/image/2026-06-05/source.png',
        )

    @patch('apps.workflows.node_executors.execute_video_generation.create_ai_client_for_user')
    @patch('apps.workflows.node_executors.execute_video_generation._pick_provider')
    def test_video_generation_converts_storage_image_to_base64(self, mock_pick_provider, mock_create_client):
        with tempfile.TemporaryDirectory() as storage_root:
            image_path = Path(storage_root) / 'image' / '2026-06-05' / 'source.png'
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(b'\x89PNG\r\n\x1a\nlocal-image')

            mock_pick_provider.return_value = SimpleNamespace(
                id=uuid.uuid4(),
                name='Video Provider',
                provider_type='image2video',
                get_provider_type_display=lambda: '图生视频',
                model_name='video-model',
                api_url='https://example.com/v1/videos',
                api_key='secret',
            )
            client = SimpleNamespace(
                _generate_video=lambda **kwargs: {
                    'success': True,
                    'data': [{'url': '/api/v1/content/storage/video/2026-06-05/generated.mp4'}],
                    'metadata': {'request_kwargs': kwargs},
                }
            )
            mock_create_client.return_value = client

            with override_settings(STORAGE_ROOT=Path(storage_root)):
                result = execute_video_generation({
                    'prompt': '生成视频',
                    'model': 'video-model',
                    'image_urls': ['/api/v1/content/storage/image/2026-06-05/source.png'],
                })

        request_kwargs = result['output_payload']['metadata']['request_kwargs']
        self.assertEqual(request_kwargs['image_mime_type'], 'image/png')
        self.assertEqual(len(request_kwargs['image_base64s']), 1)
        self.assertEqual(result['normalized_output']['image_urls'], ['/api/v1/content/storage/image/2026-06-05/source.png'])

    @patch('apps.workflows.node_executors.execute_video_generation.create_ai_client_for_user')
    @patch('apps.workflows.node_executors.execute_video_generation._pick_provider')
    def test_video_generation_prefers_upstream_text_over_default_prompt(self, mock_pick_provider, mock_create_client):
        mock_pick_provider.return_value = SimpleNamespace(
            id=uuid.uuid4(),
            name='Video Provider',
            provider_type='image2video',
            get_provider_type_display=lambda: '图生视频',
            model_name='video-model',
            api_url='https://example.com/v1/videos',
            api_key='secret',
        )
        captured_kwargs = {}

        def fake_generate_video(**kwargs):
            captured_kwargs.update(kwargs)
            return {
                'success': True,
                'data': [{'url': 'https://cdn.example.com/generated.mp4'}],
                'metadata': {},
            }

        mock_create_client.return_value = SimpleNamespace(_generate_video=fake_generate_video)

        result = execute_video_generation({
            'prompt': '生成视频',
            'text': '上游文本节点传来的真实提示词',
            'model': 'video-model',
            'image_urls': ['https://cdn.example.com/source.png'],
        })

        self.assertEqual(captured_kwargs['prompt'], '上游文本节点传来的真实提示词')
        self.assertEqual(result['normalized_output']['prompt'], '上游文本节点传来的真实提示词')

    @patch('apps.workflows.node_executors.execute_video_generation.create_ai_client_for_user')
    @patch('apps.workflows.node_executors.execute_video_generation._pick_provider')
    def test_ucloud_video_accepts_text_content_and_reports_delivered_resolution(self, mock_pick_provider, mock_create_client):
        mock_pick_provider.return_value = SimpleNamespace(
            id=uuid.uuid4(), name='优云智算 H3', provider_type='image2video',
            get_provider_type_display=lambda: '图生视频', model_name='MiniMax-H3',
            executor_class='core.ai_client.ucloud_h3_client.UCloudH3Client',
        )
        mock_create_client.return_value._generate_video.return_value = {
            'success': True,
            'data': [{'url': 'https://example.com/video.mp4', 'resolution': '768P'}],
            'metadata': {'task_id': 'task-1'},
        }
        content = [{'type': 'text', 'text': '海边日落'}]

        result = execute_video_generation({
            'model': 'MiniMax-H3', 'content': content, 'resolution': '4K',
            'use_context_ir': True,
        })

        kwargs = mock_create_client.return_value._generate_video.call_args.kwargs
        self.assertEqual(kwargs['content'], content)
        self.assertIs(kwargs['use_context_ir'], True)
        self.assertEqual(result['normalized_output']['resolution'], '768P')


class WorkflowNodeSchemaRuntimeTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='schema-runtime-user', password='secret123')
        self.series = Series.objects.create(name='结构作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.canvas = WorkflowCanvas.objects.create(
            name='结构画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.node_schema = WorkflowNodeSchema.objects.create(
            key='split_scene',
            name='拆场景',
            created_by=self.user,
            schema_config={
                'output_schema': {
                    'output_type': 'collection',
                    'items_path': 'items',
                    'source_text_path': 'source_text',
                    'summary_path': 'summary',
                },
                'materialization': {
                    'mode': 'per_item_subgraph',
                    'graph': {
                        'nodes': [
                            {
                                'node_key': 'scene:{{ index }}',
                                'node_type': 'rewrite',
                                'title': '{{ item.title }}',
                                'position_x': 480,
                                'position_y': '{{ index * 120 }}',
                                'config_data': {
                                    'instruction': '{{ item.prompt }}',
                                },
                            }
                        ],
                        'edges': [
                            {
                                'edge_key': 'edge:parent:{{ index }}',
                                'source_node': '$parent',
                                'target_node': 'scene:{{ index }}',
                            }
                        ],
                    },
                },
            },
        )
        self.node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='split_node',
            node_type='audio',
            title='拆分',
            config_data={'node_schema_key': self.node_schema.key},
        )
        self.node_run = WorkflowNodeRun.objects.create(
            canvas=self.canvas,
            node=self.node,
            node_key=self.node.node_key,
            node_type=self.node.node_type,
            status='running',
            sequence=1,
        )

    def test_finalize_success_normalizes_schema_output_without_materializing_subgraph(self):
        finalize_success(
            str(self.node_run.id),
            output_payload={},
            normalized_output={
                'source_text': '全文',
                'summary': '摘要',
                'items': [
                    {
                        'title': '第一场',
                        'prompt': '扩写第一场',
                    }
                ],
            },
        )

        self.node_run.refresh_from_db()
        self.assertEqual(self.node_run.normalized_output['schema_output']['source_text'], '全文')
        self.assertEqual(self.node_run.normalized_output['schema_output']['summary'], '摘要')
        self.assertEqual(self.node_run.normalized_output['node_schema']['key'], 'split_scene')
        self.assertFalse(WorkflowNode.objects.filter(canvas=self.canvas, node_key='scene:1').exists())
        self.assertFalse(WorkflowEdge.objects.filter(canvas=self.canvas, edge_key='edge:parent:1').exists())
        self.assertFalse(WorkflowNodeRunEvent.objects.filter(
            node_run=self.node_run,
            event_type='schema_materialized',
        ).exists())


class WorkflowRuntimeEventAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='runtime-event-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='测试作品', description='desc', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='第1集',
            original_topic='原始文案',
        )
        initialize_project(self.project)
        self.canvas = WorkflowCanvas.objects.create(
            name='事件画板',
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='active',
        )
        self.workflow_run = WorkflowRun.objects.create(
            project=self.project,
            series=self.series,
            created_by=self.user,
            status='completed',
        )
        self.node = WorkflowNode.objects.create(
            canvas=self.canvas,
            node_key='rewrite_node',
            node_type='rewrite',
            title='改写',
            status='completed',
        )
        self.node_run = WorkflowNodeRun.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.node,
            node_key='rewrite_node',
            node_type='rewrite',
            status='completed',
            external_task_id='celery-node-task-rt-1',
        )
        self.event = WorkflowNodeRunEvent.objects.create(
            workflow_run=self.workflow_run,
            canvas=self.canvas,
            node=self.node,
            node_run=self.node_run,
            event_type='run_completed',
            payload={'task_id': 'celery-node-task-rt-1'},
        )

    def test_list_node_run_events(self):
        response = self.client.get(reverse('workflow-node-run-event-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data.get('results', response.data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['event_type'], 'run_completed')
        self.assertEqual(str(items[0]['node_run']), str(self.node_run.id))

    def test_workflow_run_stream_returns_event_and_terminal_message(self):
        response = self.client.get(
            reverse('workflow-run-stream', args=[self.workflow_run.id]),
            HTTP_ACCEPT='text/event-stream',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload_text = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('"type": "connected"', payload_text)
        self.assertIn('"type": "run_completed"', payload_text)
        self.assertIn('"type": "pipeline_done"', payload_text)
        self.assertIn(str(self.workflow_run.id), payload_text)

    def test_canvas_stream_returns_event_and_terminal_message(self):
        response = self.client.get(
            reverse('workflow-canvas-stream', args=[self.canvas.id]),
            HTTP_ACCEPT='text/event-stream',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload_text = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('"type": "connected"', payload_text)
        self.assertIn('"type": "run_completed"', payload_text)
        self.assertIn('"type": "pipeline_done"', payload_text)
        self.assertIn(str(self.canvas.id), payload_text)
