from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.content.models import CameraMovement, ContentRewrite, EditedImage, GeneratedImage, GeneratedVideo, MultiGridImageTask, MultiGridTile, Storyboard
from apps.projects.tasks import _get_missing_image_storyboard_ids, _get_missing_video_storyboard_ids
from apps.projects.models import EpisodeTaskQueue, Project, ProjectStage, Series
from apps.projects.utils import get_project_stage_order, normalize_stage_template_states


User = get_user_model()


def initialize_project(project):
    for stage_type in ['rewrite', 'storyboard', 'image_generation', 'multi_grid_image', 'camera_movement', 'video_generation', 'image_edit']:
        ProjectStage.objects.create(project=project, stage_type=stage_type, status='pending')
    ContentRewrite.objects.create(project=project, original_text=project.original_topic)


class ProjectQueueAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='queue-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='三国演义', description='测试', user=self.user)
        self.project1 = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='桃园结义',
            name='第1集',
            original_topic='刘关张结义',
        )
        self.project2 = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=2,
            sort_order=2,
            episode_title='讨伐董卓',
            name='第2集',
            original_topic='群雄起兵',
        )
        initialize_project(self.project1)
        initialize_project(self.project2)

    @patch('apps.projects.tasks.run_full_pipeline_task.delay')
    def test_run_pipeline_enqueues_second_episode(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-task-1')

        first_response = self.client.post(
            reverse('project-run-pipeline', args=[self.project1.id]),
            {},
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(first_response.data['queue_status'], 'running')
        self.assertEqual(first_response.data['queue_position'], 1)
        self.assertEqual(first_response.data['task_id'], 'celery-task-1')

        second_response = self.client.post(
            reverse('project-run-pipeline', args=[self.project2.id]),
            {},
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second_response.data['queue_status'], 'waiting')
        self.assertEqual(second_response.data['queue_position'], 2)
        self.assertIsNone(second_response.data['task_id'])

        self.project1.refresh_from_db()
        self.project2.refresh_from_db()
        self.assertEqual(self.project1.status, 'processing')
        self.assertEqual(self.project2.status, 'queued')

        queue_items = EpisodeTaskQueue.objects.filter(series=self.series).order_by('created_at')
        self.assertEqual(queue_items.count(), 2)
        self.assertEqual(queue_items[0].status, 'running')
        self.assertEqual(queue_items[1].status, 'waiting')

        list_response = self.client.get(reverse('project-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        project_map = {item['id']: item for item in list_response.data.get('results', list_response.data)}
        self.assertEqual(project_map[str(self.project1.id)]['queue_status'], 'running')
        self.assertEqual(project_map[str(self.project2.id)]['queue_status'], 'waiting')
        self.assertEqual(project_map[str(self.project2.id)]['queue_position'], 2)

    @patch('apps.projects.tasks.run_full_pipeline_task.delay')
    def test_run_pipeline_returns_existing_queue_task_for_same_project(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-task-1')

        self.client.post(reverse('project-run-pipeline', args=[self.project1.id]), {}, format='json')
        response = self.client.post(reverse('project-run-pipeline', args=[self.project1.id]), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['queue_status'], 'running')
        self.assertEqual(EpisodeTaskQueue.objects.filter(project=self.project1, status__in=['waiting', 'running']).count(), 1)

    @patch('apps.projects.queue_service._is_task_visible_to_workers', return_value=False)
    @patch('apps.projects.queue_service.AsyncResult')
    @patch('apps.projects.tasks.run_full_pipeline_task.delay')
    def test_run_pipeline_recovers_stale_running_task(self, mock_delay, mock_async_result, _mock_visible):
        mock_delay.return_value = SimpleNamespace(id='celery-task-2')
        mock_async_result.return_value.state = 'PENDING'

        stale_task = EpisodeTaskQueue.objects.create(
            series=self.series,
            project=self.project1,
            task_type='pipeline',
            status='running',
            celery_task_id='stale-task-id',
            created_by=self.user,
        )
        EpisodeTaskQueue.objects.filter(id=stale_task.id).update(
            started_at=stale_task.created_at - __import__('datetime').timedelta(minutes=5)
        )
        Project.objects.filter(id=self.project1.id).update(status='processing')

        response = self.client.post(
            reverse('project-run-pipeline', args=[self.project2.id]),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['queue_status'], 'running')
        self.assertEqual(response.data['task_id'], 'celery-task-2')

        stale_task.refresh_from_db()
        self.project1.refresh_from_db()
        self.project2.refresh_from_db()

        self.assertEqual(stale_task.status, 'failed')
        self.assertEqual(self.project1.status, 'failed')
        self.assertEqual(self.project2.status, 'processing')


    @patch('apps.projects.tasks.run_full_pipeline_task.delay')
    def test_force_release_running_queue_task(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-task-1')

        self.client.post(reverse('project-run-pipeline', args=[self.project1.id]), {}, format='json')
        self.client.post(reverse('project-run-pipeline', args=[self.project2.id]), {}, format='json')

        response = self.client.post(
            reverse('project-force-release-queue', args=[self.project1.id]),
            {'reason': '管理员手动释放'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first_task = EpisodeTaskQueue.objects.filter(project=self.project1).order_by('created_at').first()
        second_task = EpisodeTaskQueue.objects.filter(project=self.project2).order_by('created_at').first()
        self.project1.refresh_from_db()
        self.project2.refresh_from_db()

        self.assertEqual(first_task.status, 'failed')
        self.assertEqual(second_task.status, 'running')
        self.assertEqual(self.project1.status, 'failed')
        self.assertEqual(self.project2.status, 'processing')

    @patch('apps.projects.tasks.run_full_pipeline_task.delay')
    def test_retry_pipeline_requeues_project(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-task-9')
        self.project1.status = 'failed'
        self.project1.completed_at = __import__('django.utils.timezone').utils.timezone.now()
        self.project1.save(update_fields=['status', 'completed_at', 'updated_at'])
        self.project1.stages.filter(stage_type='rewrite').update(status='failed', error_message='旧错误')

        response = self.client.post(
            reverse('project-retry-pipeline', args=[self.project1.id]),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['queue_status'], 'running')
        self.assertEqual(response.data['task_id'], 'celery-task-9')

        self.project1.refresh_from_db()
        rewrite_stage = self.project1.stages.get(stage_type='rewrite')
        self.assertEqual(self.project1.status, 'processing')
        self.assertEqual(rewrite_stage.status, 'pending')
        self.assertEqual(rewrite_stage.error_message, '')


class ImageRegenerateBehaviorTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='image-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='图片重生成', description='测试', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='图片项目',
            original_topic='测试图片重生成',
        )
        initialize_project(self.project)
        self.storyboard = Storyboard.objects.create(
            project=self.project,
            sequence_number=1,
            scene_description='场景1',
            narration_text='旁白1',
            image_prompt='提示词1',
        )

    def test_get_missing_image_storyboard_ids_skips_completed_by_default(self):
        GeneratedImage.objects.create(
            storyboard=self.storyboard,
            image_url='https://example.com/image-1.png',
            generation_params={},
            status='completed',
        )

        result = _get_missing_image_storyboard_ids(self.project, [str(self.storyboard.id)])

        self.assertEqual(result, [])

    def test_get_missing_image_storyboard_ids_includes_completed_when_forced(self):
        GeneratedImage.objects.create(
            storyboard=self.storyboard,
            image_url='https://example.com/image-1.png',
            generation_params={},
            status='completed',
        )

        result = _get_missing_image_storyboard_ids(
            self.project,
            [str(self.storyboard.id)],
            force_regenerate=True,
        )

        self.assertEqual(result, [str(self.storyboard.id)])

    @patch('apps.projects.views.is_stage_template_enabled', return_value=True)
    @patch('apps.projects.tasks.execute_text2image_stage.delay')
    def test_execute_stage_passes_force_regenerate_flag(self, mock_delay, _mock_stage_enabled):
        mock_delay.return_value = SimpleNamespace(id='celery-image-task')

        response = self.client.post(
            reverse('project-execute-stage', args=[self.project.id]),
            {
                'stage_name': 'image_generation',
                'input_data': {
                    'storyboard_ids': [str(self.storyboard.id)],
                    'force_regenerate': True,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(
            project_id=str(self.project.id),
            storyboard_ids=[str(self.storyboard.id)],
            force_regenerate=True,
            user_id=self.user.id,
        )


    def test_get_missing_video_storyboard_ids_skips_completed_by_default(self):
        image = GeneratedImage.objects.create(
            storyboard=self.storyboard,
            image_url='https://example.com/image-1.png',
            generation_params={},
            status='completed',
        )
        camera_movement = CameraMovement.objects.create(
            storyboard=self.storyboard,
            movement_type='static',
            movement_params={},
        )
        GeneratedVideo.objects.create(
            storyboard=self.storyboard,
            image=image,
            camera_movement=camera_movement,
            video_url='https://example.com/video-1.mp4',
            generation_params={},
            status='completed',
        )

        result = _get_missing_video_storyboard_ids(self.project, [str(self.storyboard.id)])

        self.assertEqual(result, [])

    def test_get_missing_video_storyboard_ids_includes_completed_when_forced(self):
        image = GeneratedImage.objects.create(
            storyboard=self.storyboard,
            image_url='https://example.com/image-1.png',
            generation_params={},
            status='completed',
        )
        camera_movement = CameraMovement.objects.create(
            storyboard=self.storyboard,
            movement_type='static',
            movement_params={},
        )
        GeneratedVideo.objects.create(
            storyboard=self.storyboard,
            image=image,
            camera_movement=camera_movement,
            video_url='https://example.com/video-1.mp4',
            generation_params={},
            status='completed',
        )

        result = _get_missing_video_storyboard_ids(
            self.project,
            [str(self.storyboard.id)],
            force_regenerate=True,
        )

        self.assertEqual(result, [str(self.storyboard.id)])

    @patch('apps.projects.views.is_stage_template_enabled', return_value=True)
    @patch('apps.projects.tasks.execute_image2video_stage.delay')
    def test_execute_stage_passes_video_force_regenerate_flag(self, mock_delay, _mock_stage_enabled):
        mock_delay.return_value = SimpleNamespace(id='celery-video-task')

        response = self.client.post(
            reverse('project-execute-stage', args=[self.project.id]),
            {
                'stage_name': 'video_generation',
                'input_data': {
                    'storyboard_ids': [str(self.storyboard.id)],
                    'force_regenerate': True,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(
            project_id=str(self.project.id),
            storyboard_ids=[str(self.storyboard.id)],
            force_regenerate=True,
            user_id=self.user.id,
        )


class ProjectStageFlowRuleTestCase(APITestCase):
    def test_normalize_stage_template_states_prefers_advanced_image_flow(self):
        normalized = normalize_stage_template_states({
            'rewrite': True,
            'storyboard': True,
            'image_generation': True,
            'multi_grid_image': True,
            'image_edit': True,
            'camera_movement': True,
            'video_generation': True,
        })

        self.assertFalse(normalized['image_generation'])
        self.assertTrue(normalized['multi_grid_image'])
        self.assertTrue(normalized['image_edit'])

    def test_get_project_stage_order_uses_advanced_image_flow_sequence(self):
        stage_order = get_project_stage_order({
            'rewrite': True,
            'storyboard': True,
            'image_generation': True,
            'multi_grid_image': True,
            'image_edit': True,
            'camera_movement': True,
            'video_generation': True,
        })

        self.assertEqual(
            stage_order,
            ['rewrite', 'storyboard', 'multi_grid_image', 'image_edit', 'camera_movement', 'video_generation']
        )

    def test_get_project_stage_order_keeps_image_generation_when_advanced_flow_disabled(self):
        stage_order = get_project_stage_order({
            'rewrite': True,
            'storyboard': True,
            'image_generation': True,
            'multi_grid_image': False,
            'image_edit': False,
            'camera_movement': True,
            'video_generation': True,
        })

        self.assertEqual(
            stage_order,
            ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']
        )



class ImageEditStageExecutionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='edit-user', password='secret123')
        self.client.force_authenticate(self.user)
        self.series = Series.objects.create(name='图片编辑项目', description='测试', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='编辑项目',
            original_topic='测试图片编辑',
        )
        initialize_project(self.project)
        self.storyboard = Storyboard.objects.create(
            project=self.project,
            sequence_number=1,
            scene_description='场景1',
            narration_text='旁白1',
            image_prompt='提示词1',
        )
        self.multi_grid_task = MultiGridImageTask.objects.create(
            storyboard=self.storyboard,
            source_image_url='https://example.com/source-grid.png',
            grid_rows=2,
            grid_cols=2,
            status='completed',
        )
        self.tile = MultiGridTile.objects.create(
            task=self.multi_grid_task,
            tile_index=1,
            row_index=0,
            col_index=0,
            crop_box={'left': 0, 'top': 0, 'right': 100, 'bottom': 100},
            tile_image_url='https://example.com/tile-1.png',
            status='completed',
            width=100,
            height=100,
        )

    @patch('apps.projects.views.is_stage_template_enabled', return_value=True)
    @patch('apps.projects.tasks.execute_image_edit_stage.delay')
    def test_execute_stage_dispatches_image_edit_task(self, mock_delay, _mock_stage_enabled):
        mock_delay.return_value = SimpleNamespace(id='celery-image-edit-task')

        response = self.client.post(
            reverse('project-execute-stage', args=[self.project.id]),
            {
                'stage_name': 'image_edit',
                'input_data': {
                    'storyboard_ids': [str(self.storyboard.id)],
                    'force_regenerate': True,
                    'strength': 0.5,
                    'width': 2048,
                    'height': 2048,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(
            project_id=str(self.project.id),
            storyboard_ids=[str(self.storyboard.id)],
            force_regenerate=True,
            user_id=self.user.id,
            strength=0.5,
            width=2048,
            height=2048,
        )

    @patch('apps.content.processors.image_edit_stage.create_ai_client')
    def test_image_edit_processor_creates_edited_images_from_tiles(self, mock_create_ai_client):
        from core.ai_client.base import AIResponse
        from apps.models.models import ModelProvider
        from apps.prompts.models import PromptTemplate, PromptTemplateSet
        from apps.content.processors.image_edit_stage import ImageEditStageProcessor

        provider = ModelProvider.objects.create(
            name='Mock Image Edit API',
            provider_type='image_edit',
            api_url='https://example.com/edit',
            api_key='test-key',
            model_name='mock-image-edit',
            executor_class='core.ai_client.mock_image_edit_client.MockImageEditClient',
            is_active=True,
        )
        template_set = PromptTemplateSet.objects.create(
            name='图片编辑模板集',
            created_by=self.user,
            is_active=True,
            is_default=True,
        )
        PromptTemplate.objects.create(
            template_set=template_set,
            stage_type='image_edit',
            model_provider=provider,
            template_content='高清修复 {{ tile_image_url }}',
            is_active=True,
        )
        self.project.prompt_template_set = template_set
        self.project.save(update_fields=['prompt_template_set'])

        mock_client = mock_create_ai_client.return_value
        mock_client.generate.return_value = AIResponse(
            success=True,
            data=[{'url': 'https://example.com/edited-tile-1.png', 'width': 2048, 'height': 2048}],
            metadata={'provider': 'mock'},
        )

        processor = ImageEditStageProcessor()
        result = list(processor.process_stream(project_id=str(self.project.id), storyboard_ids=[str(self.storyboard.id)], force_regenerate=True, width=2048, height=2048))

        self.assertTrue(any(item.get('type') == 'image_edited' for item in result))
        self.assertTrue(any(item.get('type') == 'done' for item in result))

        edited_image = EditedImage.objects.get(multi_grid_tile=self.tile)
        self.assertEqual(edited_image.storyboard, self.storyboard)
        self.assertEqual(edited_image.source_stage_type, 'multi_grid_image')
        self.assertEqual(edited_image.source_image_url, 'https://example.com/tile-1.png')
        self.assertEqual(edited_image.edited_image_url, 'https://example.com/edited-tile-1.png')
        self.assertEqual(edited_image.width, 2048)
        self.assertEqual(edited_image.height, 2048)
