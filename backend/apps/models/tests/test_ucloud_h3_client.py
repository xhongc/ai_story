from unittest.mock import patch

from django.test import SimpleTestCase

from core.ai_client.ucloud_h3_client import UCloudH3Client


class UCloudH3ClientTests(SimpleTestCase):
    def setUp(self):
        self.client = UCloudH3Client(
            api_url='https://cp.compshare.cn/minimax/v2/video_generation',
            api_token='sk-ml-test', model='MiniMax-H3',
        )

    def test_requires_video_workbench_api_key(self):
        with self.assertRaisesRegex(ValueError, 'sk-ml-'):
            UCloudH3Client(
                api_url='https://cp.compshare.cn/minimax/v2/video_generation',
                api_token='sk-other', model='MiniMax-H3',
            )

    @patch('core.ai_client.image2video_client.VideoGeneratorClient._localize_video_data', side_effect=lambda data, timeout: data)
    @patch('core.ai_client.ucloud_h3_client.requests.get')
    @patch('core.ai_client.ucloud_h3_client.requests.post')
    def test_first_and_last_frame_video_lifecycle(self, mock_post, mock_get, _localize):
        mock_post.return_value.json.return_value = {'task_id': 'task-123'}
        mock_get.return_value.json.side_effect = [
            {'task': {'status': 'moderating'}},
            {'task': {'status': 'succeeded', 'resolution': '4K',
                      'content': {'url': 'https://example.com/video.mp4'}}},
        ]
        with patch('core.ai_client.ucloud_h3_client.time.sleep'):
            result = self.client._generate_video(
                prompt='猫走路', image_uri='https://example.com/first.png',
                image_uris=['https://example.com/first.png', 'https://example.com/last.png'],
                duration_seconds=30, resolution='4K', aspect_ratio='9:16',
                generate_audio=False, use_context_ir=True,
                idempotency_key='video-123',
            )

        self.assertEqual(mock_post.call_args.args[0], 'https://cp.compshare.cn/minimax/v2/video_generation')
        self.assertEqual(mock_post.call_args.kwargs['headers']['Authorization'], 'Bearer sk-ml-test')
        self.assertEqual(mock_post.call_args.kwargs['headers']['Idempotency-Key'], 'video-123')
        self.assertEqual(mock_post.call_args.kwargs['json'], {
            'model': 'MiniMax-H3',
            'content': [
                {'type': 'text', 'text': '猫走路'},
                {'type': 'image_url', 'image_url': {'url': 'https://example.com/first.png'}, 'role': 'first_frame'},
                {'type': 'image_url', 'image_url': {'url': 'https://example.com/last.png'}, 'role': 'last_frame'},
            ],
            'resolution': '4K', 'duration': 30, 'ratio': '9:16',
            'use_context_ir': True, 'mute_audio': True,
        })
        self.assertEqual(mock_get.call_args.args[0], 'https://cp.compshare.cn/minimax/v2/query/video_generation/task-123')
        self.assertEqual(result['data'], [
            {'url': 'https://example.com/video.mp4', 'resolution': '4K'},
        ])

    @patch('core.ai_client.ucloud_h3_client.requests.post')
    def test_text_and_reference_content(self, mock_post):
        mock_post.return_value.json.return_value = {'task_id': 'task-456'}
        content = [
            {'type': 'text', 'text': '参考 <Picture 1> 和 <Audio 1>'},
            {'type': 'image_url', 'image_url': {'url': 'https://example.com/person.png'}, 'role': 'reference_image'},
            {'type': 'audio_url', 'audio_url': {'url': 'https://example.com/voice.mp3'}, 'role': 'reference_audio'},
        ]
        self.client.create_video_task('', content=content, skill_id='skill-1', use_context_ir=True)
        self.assertEqual(mock_post.call_args.kwargs['json']['content'], content)
        self.assertEqual(mock_post.call_args.kwargs['json']['skill_id'], 'skill-1')
        self.client.create_video_task('纯文本视频')
        self.assertEqual(mock_post.call_args.kwargs['json']['content'], [{'type': 'text', 'text': '纯文本视频'}])
        self.client.create_video_task('', image_uri='https://example.com/first.png')
        self.assertEqual(mock_post.call_args.kwargs['json']['content'], [
            {'type': 'image_url', 'image_url': {'url': 'https://example.com/first.png'}, 'role': 'first_frame'},
        ])

    @patch('core.ai_client.image2video_client.Path.read_bytes', return_value=b'first-frame')
    @patch('core.ai_client.ucloud_h3_client.requests.post')
    def test_local_first_frame_keeps_order(self, mock_post, _read_bytes):
        mock_post.return_value.json.return_value = {'task_id': 'task-123'}
        self.client.create_video_task(
            'prompt', image_uris=[
                '/api/v1/content/storage/image/first.png',
                'https://example.com/last.png',
            ],
        )
        content = mock_post.call_args.kwargs['json']['content']
        self.assertEqual(content[1]['role'], 'first_frame')
        self.assertTrue(content[1]['image_url']['url'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(content[2]['role'], 'last_frame')

    def test_invalid_inputs_do_not_submit(self):
        with patch('core.ai_client.ucloud_h3_client.requests.post') as mock_post:
            for kwargs in ({'duration_seconds': 31}, {'resolution': '720P'},
                           {'skill_id': 'skill-1'},
                           {'content': [
                               {'type': 'image_url', 'image_url': {'url': 'https://example.com/a.png'}, 'role': 'first_frame'},
                               {'type': 'image_url', 'image_url': {'url': 'https://example.com/b.png'}, 'role': 'reference_image'},
                           ]}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.client.create_video_task('prompt', **kwargs)
            mock_post.assert_not_called()

    @patch('core.ai_client.ucloud_h3_client.requests.get')
    def test_blocked_task_stops_polling_with_error(self, mock_get):
        mock_get.return_value.json.return_value = {
            'task': {'status': 'blocked', 'error': {'message': '内容未通过审核'}}
        }
        with self.assertRaisesRegex(RuntimeError, '内容未通过审核'):
            self.client.wait_for_completion('task-123', poll_interval=0)
        mock_get.assert_called_once()

    @patch('core.ai_client.ucloud_h3_client.requests.post')
    def test_business_error_is_not_treated_as_created_task(self, mock_post):
        mock_post.return_value.json.return_value = {'RetCode': 8039, 'Message': 'job not found'}
        with self.assertRaisesRegex(ValueError, 'job not found'):
            self.client.create_video_task('prompt')
