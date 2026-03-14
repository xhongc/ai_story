from unittest.mock import patch

from django.test import TestCase

from apps.models.models import ModelProvider
from apps.models.services import ModelProviderService
from core.ai_client.base import AIResponse


class ModelProviderServiceImage2VideoTestCase(TestCase):
    async def test_image2video_provider_uses_comfyui_executor(self):
        provider = ModelProvider(
            name='ComfyUI Video',
            provider_type='image2video',
            api_url='http://localhost:8188',
            api_key='secret',
            model_name='workflow-model',
            executor_class='core.ai_client.comfyui_client.ComfyUIClient',
            timeout=30,
            extra_config={
                'test_image_url': 'http://example.com/test.png',
                'fps': 12,
                'duration': 3,
            },
        )

        with patch('core.ai_client.comfyui_client.ComfyUIClient._generate_video', return_value=AIResponse(success=True, data=[{'url': 'http://example.com/video.mp4'}], metadata={'foo': 'bar'})) as mock_generate:
            result = await ModelProviderService._test_image2video_provider(provider, 'render prompt')

        self.assertTrue(result['success'])
        self.assertEqual(result['data']['videos'][0]['url'], 'http://example.com/video.mp4')
        self.assertEqual(result['data']['test_image_url'], 'http://example.com/test.png')
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs['image_url'], 'http://example.com/test.png')

    async def test_image2video_provider_uses_video_generator_client(self):
        provider = ModelProvider(
            name='Video API',
            provider_type='image2video',
            api_url='http://localhost:9000',
            api_key='secret',
            model_name='video-model',
            executor_class='core.ai_client.image2video_client.VideoGeneratorClient',
            timeout=30,
            extra_config={
                'test_image_url': 'http://example.com/test.png',
                'fps': 24,
                'duration': 5,
                'aspect_ratio': '9:16',
            },
        )

        with patch('core.ai_client.image2video_client.VideoGeneratorClient._generate_video', return_value={'success': True, 'data': [{'url': 'http://example.com/video-api.mp4'}], 'metadata': {}}) as mock_generate:
            result = await ModelProviderService._test_image2video_provider(provider, 'animate prompt')

        self.assertTrue(result['success'])
        self.assertEqual(result['data']['videos'][0]['url'], 'http://example.com/video-api.mp4')
        self.assertEqual(result['data']['metadata']['aspect_ratio'], '9:16')
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs['image_uri'], 'http://example.com/test.png')
