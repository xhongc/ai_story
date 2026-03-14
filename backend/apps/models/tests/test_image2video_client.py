from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from core.ai_client.image2video_client import VideoGeneratorClient


class VideoGeneratorClientTestCase(SimpleTestCase):
    @patch('core.ai_client.image2video_client.requests.post')
    def test_chat_completions_endpoint_extracts_video_url(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': '<video src="https://example.com/generated.mp4" controls="controls"></video>'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        client = VideoGeneratorClient(
            api_url='https://freeapi.example.com/v1/chat/completions',
            api_token='secret',
            model='grok-imagine-1.0-video',
        )

        result = client._generate_video(
            prompt='狗狗动起来',
            image_base64='ZmFrZV9pbWFnZV9iYXNlNjQ=',
            camera_movement_description='镜头缓慢推进，主体保持居中',
            model='grok-imagine-1.0-video',
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['data'], [{'url': 'https://example.com/generated.mp4'}])
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0],
            'https://freeapi.example.com/v1/chat/completions',
        )
        self.assertEqual(
            mock_post.call_args.kwargs['json']['messages'][0]['content'][1]['image_url']['url'],
            'data:image/jpeg;base64,ZmFrZV9pbWFnZV9iYXNlNjQ=',
        )
        self.assertIn(
            '运镜描述：镜头缓慢推进，主体保持居中',
            mock_post.call_args.kwargs['json']['messages'][0]['content'][0]['text'],
        )

    @patch('core.ai_client.image2video_client.requests.post')
    def test_video_generations_endpoint_keeps_original_url(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'data': {
                'task_id': 'task-123'
            }
        }
        mock_post.return_value = mock_response

        client = VideoGeneratorClient(
            api_url='https://video.example.com/v1/video/generations',
            api_token='secret',
            model='video-model',
        )

        task_result = client.create_video_task(
            prompt='狗狗动起来',
            image_uri='https://example.com/source.png',
            image_base64='ZmFrZV9pbWFnZV9iYXNlNjQ=',
            camera_movement_description='镜头轻微右移',
            model='video-model',
        )

        self.assertEqual(task_result, 'task-123')
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0],
            'https://video.example.com/v1/video/generations',
        )
        self.assertEqual(
            mock_post.call_args.kwargs['json']['imageBase64'],
            'ZmFrZV9pbWFnZV9iYXNlNjQ=',
        )
        self.assertEqual(
            mock_post.call_args.kwargs['json']['cameraMovementDescription'],
            '镜头轻微右移',
        )
