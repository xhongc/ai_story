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
            image_uri='https://example.com/source.png',
            model='grok-imagine-1.0-video',
        )

        self.assertEqual(result, ['https://example.com/generated.mp4'])
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0],
            'https://freeapi.example.com/v1/chat/completions',
        )
        self.assertEqual(
            mock_post.call_args.kwargs['json']['messages'][0]['content'][1]['image_url']['url'],
            'https://example.com/source.png',
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

        task_id = client.create_video_task(
            prompt='狗狗动起来',
            image_uri='https://example.com/source.png',
            model='video-model',
        )

        self.assertEqual(task_id, 'task-123')
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.args[0],
            'https://video.example.com/v1/video/generations',
        )
