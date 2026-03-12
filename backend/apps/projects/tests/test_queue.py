from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.content.models import ContentRewrite
from apps.projects.models import EpisodeTaskQueue, Project, ProjectStage, Series


User = get_user_model()


def initialize_project(project):
    for stage_type in ['rewrite', 'storyboard', 'image_generation', 'camera_movement', 'video_generation']:
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
