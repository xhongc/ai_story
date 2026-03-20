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

    async def test_image2video_provider_prefers_explicit_base64_input(self):
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
            },
        )

        with patch('core.ai_client.image2video_client.VideoGeneratorClient._generate_video', return_value={'success': True, 'data': [{'url': 'http://example.com/video-api.mp4'}], 'metadata': {}}) as mock_generate:
            result = await ModelProviderService._test_image2video_provider(
                provider,
                'animate prompt',
                test_image_base64='ZmFrZV9pbWFnZV9iYXNlNjQ=',
                test_image_mime_type='image/png',
            )

        self.assertTrue(result['success'])
        self.assertTrue(result['data']['test_image_base64_provided'])
        self.assertEqual(result['data']['test_image_mime_type'], 'image/png')
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs['image_uri'], 'http://example.com/test.png')
        self.assertEqual(mock_generate.call_args.kwargs['image_base64'], 'ZmFrZV9pbWFnZV9iYXNlNjQ=')
        self.assertEqual(mock_generate.call_args.kwargs['image_mime_type'], 'image/png')

    async def test_image2video_provider_uses_default_test_image_when_missing_input(self):
        provider = ModelProvider(
            name='Video API',
            provider_type='image2video',
            api_url='http://localhost:9000',
            api_key='secret',
            model_name='video-model',
            executor_class='core.ai_client.image2video_client.VideoGeneratorClient',
            timeout=30,
            extra_config={
                'fps': 24,
                'duration': 5,
            },
        )

        with patch(
            'apps.models.services.ModelProviderService._load_default_image2video_test_image',
            return_value={
                'image_base64': 'ZGVmYXVsdC1pbWFnZS1iYXNlNjQ=',
                'image_mime_type': 'image/jpeg',
                'image_path': '/tmp/test.jpeg',
            }
        ), patch('core.ai_client.image2video_client.VideoGeneratorClient._generate_video', return_value={'success': True, 'data': [{'url': 'http://example.com/video-api.mp4'}], 'metadata': {}}) as mock_generate:
            result = await ModelProviderService._test_image2video_provider(provider, 'animate prompt')

        self.assertTrue(result['success'])
        self.assertTrue(result['data']['test_image_base64_provided'])
        self.assertTrue(result['data']['used_default_test_image'])
        self.assertEqual(result['data']['test_image_url'], '')
        self.assertEqual(mock_generate.call_args.kwargs['image_base64'], 'ZGVmYXVsdC1pbWFnZS1iYXNlNjQ=')
        self.assertEqual(mock_generate.call_args.kwargs['image_mime_type'], 'image/jpeg')

    async def test_image2video_provider_uses_volcengine_executor(self):
        provider = ModelProvider(
            name='Volcengine Video API',
            provider_type='image2video',
            api_url='https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
            api_key='secret',
            model_name='doubao-seedance-1-5-pro-251215',
            executor_class='core.ai_client.volcengine_image2video_client.VolcengineImage2VideoClient',
            timeout=30,
            extra_config={
                'test_image_url': 'http://example.com/test.png',
                'duration': 5,
                'aspect_ratio': '16:9',
                'resolution': '720p',
            },
        )

        with patch('core.ai_client.volcengine_image2video_client.VolcengineImage2VideoClient._generate_video', return_value={'success': True, 'data': [{'url': 'http://example.com/volc-video.mp4'}], 'metadata': {}}) as mock_generate:
            result = await ModelProviderService._test_image2video_provider(provider, 'animate prompt')

        self.assertTrue(result['success'])
        self.assertEqual(result['data']['videos'][0]['url'], 'http://example.com/volc-video.mp4')
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs['image_uri'], 'http://example.com/test.png')



class ModelProviderServiceImageEditTestCase(TestCase):
    async def test_image_edit_provider_uses_mock_image_edit_client(self):
        provider = ModelProvider(
            name='Mock Image Edit',
            provider_type='image_edit',
            api_url='http://localhost:8010/api/mock/image-edit/',
            api_key='secret',
            model_name='mock-image-edit-v1',
            executor_class='core.ai_client.mock_image_edit_client.MockImageEditClient',
            timeout=30,
            extra_config={
                'test_image_url': 'http://example.com/input.png',
                'width': 1536,
                'height': 1536,
                'strength': 0.25,
            },
        )

        with patch(
            'core.ai_client.mock_image_edit_client.MockImageEditClient.generate',
            return_value=AIResponse(success=True, data=[{'url': 'http://example.com/output.png'}], metadata={'usage': {}})
        ) as mock_generate:
            result = await ModelProviderService._test_image_edit_provider(provider, 'enhance image')

        self.assertTrue(result['success'])
        self.assertEqual(result['data']['images'][0]['url'], 'http://example.com/output.png')
        self.assertEqual(result['data']['test_image_url'], 'http://example.com/input.png')
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.kwargs['image_url'], 'http://example.com/input.png')
        self.assertEqual(mock_generate.call_args.kwargs['width'], 1536)
        self.assertEqual(mock_generate.call_args.kwargs['height'], 1536)
