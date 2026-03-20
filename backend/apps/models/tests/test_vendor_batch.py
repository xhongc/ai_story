from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.models.models import ModelProvider, VendorConnectionConfig
from apps.models.services import ModelProviderService


User = get_user_model()


class ModelProviderVendorServiceTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vendor-user', password='secret123')
        self.client.force_authenticate(self.user)

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_returns_filtered_models(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o-mini', 'owned_by': 'openai'},
                {'id': 'tts-1', 'owned_by': 'openai'},
                {'id': 'o1-preview', 'owned_by': 'openai'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('openai', 'llm', 'sk-test')

        self.assertEqual(result['vendor'], 'openai')
        self.assertEqual(result['capability'], 'llm')
        self.assertEqual([item['id'] for item in result['models']], ['gpt-4o-mini', 'o1-preview'])
        self.assertTrue(result['models'][0]['is_capability_match'])
        self.assertTrue(result['models'][1]['is_capability_match'])

    def test_batch_create_vendor_models_skips_existing(self):
        ModelProvider.objects.create(
            name='OpenAI / gpt-4o-mini',
            provider_type='llm',
            api_url='https://api.openai.com/v1/chat/completions',
            api_key='sk-old',
            model_name='gpt-4o-mini',
            executor_class='core.ai_client.openai_client.OpenAIClient',
        )

        result = ModelProviderService.batch_create_vendor_models({
            'vendor': 'openai',
            'capability': 'llm',
            'api_key': 'sk-test',
            'model_names': ['gpt-4o-mini', 'gpt-4.1-mini'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        })

        self.assertEqual(result['created_count'], 1)
        self.assertEqual(result['skipped_count'], 1)
        self.assertEqual(result['provider_type'], 'llm')
        self.assertTrue(ModelProvider.objects.filter(model_name='gpt-4.1-mini').exists())

    def test_batch_create_vendor_models_supports_volcengine_text2image(self):
        result = ModelProviderService.batch_create_vendor_models({
            'vendor': 'volcengine',
            'capability': 'text2image',
            'api_key': 'sk-test',
            'model_names': ['doubao-seedream-3-0-t2i'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        })

        provider = ModelProvider.objects.get(model_name='doubao-seedream-3-0-t2i')
        self.assertEqual(result['created_count'], 1)
        self.assertEqual(provider.provider_type, 'text2image')
        self.assertEqual(provider.api_url, 'https://ark.cn-beijing.volces.com/api/v3/images/generations')
        self.assertEqual(provider.executor_class, 'core.ai_client.text2image_client.Text2ImageClient')

    def test_batch_create_vendor_models_supports_volcengine_image2video(self):
        result = ModelProviderService.batch_create_vendor_models({
            'vendor': 'volcengine',
            'capability': 'image2video',
            'api_key': 'sk-test',
            'model_names': ['seedance-1-0-lite-i2v'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        })

        provider = ModelProvider.objects.get(model_name='seedance-1-0-lite-i2v')
        self.assertEqual(result['created_count'], 1)
        self.assertEqual(provider.provider_type, 'image2video')
        self.assertEqual(provider.api_url, 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks')
        self.assertEqual(provider.executor_class, 'core.ai_client.volcengine_image2video_client.VolcengineImage2VideoClient')

    def test_batch_create_vendor_models_supports_gemini_multimodal(self):
        image_result = ModelProviderService.batch_create_vendor_models({
            'vendor': 'gemini',
            'capability': 'text2image',
            'api_key': 'sk-test',
            'model_names': ['imagen-3.0-generate-002'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        })
        video_result = ModelProviderService.batch_create_vendor_models({
            'vendor': 'gemini',
            'capability': 'image2video',
            'api_key': 'sk-test',
            'model_names': ['veo-3.0-fast-generate-preview'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        })

        image_provider = ModelProvider.objects.get(model_name='imagen-3.0-generate-002')
        video_provider = ModelProvider.objects.get(model_name='veo-3.0-fast-generate-preview')
        self.assertEqual(image_result['created_count'], 1)
        self.assertEqual(video_result['created_count'], 1)
        self.assertEqual(image_provider.provider_type, 'text2image')
        self.assertEqual(image_provider.executor_class, 'core.ai_client.text2image_client.Text2ImageClient')
        self.assertEqual(video_provider.provider_type, 'image2video')
        self.assertEqual(video_provider.executor_class, 'core.ai_client.image2video_client.VideoGeneratorClient')


    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_excludes_audio_and_rerank_models(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'tts-1-hd'},
                {'id': 'speech-recognition-v1'},
                {'id': 'bge-rerank-v2'},
                {'id': 'gpt-4o-mini'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('openai', 'llm', 'sk-test')

        self.assertEqual([item['id'] for item in result['models']], ['gpt-4o-mini'])

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_classifies_vlm_separately(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'doubao-1-5-vision-pro-250328', 'domain': 'VLM'},
                {'id': 'doubao-pro-32k-241215', 'domain': 'LLM'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('volcengine', 'llm', 'sk-test')

        vlm_model = next(item for item in result['models'] if item['id'] == 'doubao-1-5-vision-pro-250328')
        llm_model = next(item for item in result['models'] if item['id'] == 'doubao-pro-32k-241215')
        self.assertEqual(vlm_model['classified_capability'], 'vlm')
        self.assertEqual(vlm_model['classified_capability_label'], '视觉语言模型')
        self.assertFalse(vlm_model['is_capability_match'])
        self.assertTrue(llm_model['is_capability_match'])

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_does_not_mark_video_as_llm_match(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'doubao-seaweed-241128', 'domain': 'VideoGeneration'},
                {'id': 'doubao-pro-32k-241215', 'domain': 'LLM'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('volcengine', 'llm', 'sk-test')

        video_model = next(item for item in result['models'] if item['id'] == 'doubao-seaweed-241128')
        llm_model = next(item for item in result['models'] if item['id'] == 'doubao-pro-32k-241215')
        self.assertEqual(video_model['classified_capability'], 'image2video')
        self.assertFalse(video_model['is_capability_match'])
        self.assertTrue(llm_model['is_capability_match'])

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_filters_embedding_models(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'doubao-embedding-text-240715', 'domain': 'Embedding'},
                {'id': 'embbeding-test-model'},
                {'id': 'doubao-pro-32k-241215', 'domain': 'LLM'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('volcengine', 'llm', 'sk-test')

        self.assertEqual([item['id'] for item in result['models']], ['doubao-pro-32k-241215'])

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_prefers_vendor_metadata_classification(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'doubao-embedding-text-240715', 'domain': 'Embedding'},
                {'id': 'doubao-seaweed-241128', 'domain': 'VideoGeneration'},
                {'id': 'doubao-pro-32k-241215', 'domain': 'LLM'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('volcengine', 'image2video', 'sk-test')

        self.assertEqual(result['models'][0]['id'], 'doubao-seaweed-241128')
        self.assertEqual(result['models'][0]['classified_capability'], 'image2video')
        self.assertTrue(result['models'][0]['is_capability_match'])
        self.assertNotIn('doubao-embedding-text-240715', [item['id'] for item in result['models']])

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_marks_recommended(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gemini-2.5-pro'},
                {'id': 'imagen-3.0-generate-002'},
            ]
        }
        mock_get.return_value = mock_response

        result = ModelProviderService.discover_vendor_models('gemini', 'llm', 'sk-test')

        self.assertEqual(result['models'][0]['id'], 'gemini-2.5-pro')
        self.assertEqual(result['models'][0]['classified_capability'], 'llm')
        self.assertTrue(result['models'][0]['is_capability_match'])
        self.assertEqual(result['models'][1]['classified_capability'], 'text2image')
        self.assertFalse(result['models'][1]['is_capability_match'])


class ModelProviderVendorViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vendor-api-user', password='secret123')
        self.client.force_authenticate(self.user)

    def test_builtin_vendors_endpoint_returns_results(self):
        response = self.client.get('/api/v1/models/providers/builtin_vendors/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)
        volcengine = next(item for item in response.data['results'] if item['key'] == 'volcengine')
        capability_keys = [item['key'] for item in volcengine['capabilities']]
        self.assertIn('llm', capability_keys)
        self.assertIn('text2image', capability_keys)
        self.assertIn('image2video', capability_keys)
        vendor_keys = [item['key'] for item in response.data['results']]
        self.assertIn('gemini', vendor_keys)
        self.assertIn('grok', vendor_keys)
        self.assertIn('newapi', vendor_keys)
        self.assertIn('deepseek', vendor_keys)
        self.assertIn('minimax', vendor_keys)
        self.assertIn('modelscope', vendor_keys)
        gemini = next(item for item in response.data['results'] if item['key'] == 'gemini')
        gemini_capability_keys = [item['key'] for item in gemini['capabilities']]
        self.assertIn('text2image', gemini_capability_keys)
        self.assertIn('image2video', gemini_capability_keys)
        modelscope = next(item for item in response.data['results'] if item['key'] == 'modelscope')
        self.assertEqual(modelscope['capabilities'][0]['api_url'], 'https://api-inference.modelscope.cn/v1/chat/completions')
        openai = next(item for item in response.data['results'] if item['key'] == 'openai')
        self.assertTrue(all(item['configurable_api_url'] for item in openai['capabilities']))
        newapi = next(item for item in response.data['results'] if item['key'] == 'newapi')
        newapi_capability_keys = [item['key'] for item in newapi['capabilities']]
        self.assertIn('text2image', newapi_capability_keys)
        self.assertIn('image2video', newapi_capability_keys)

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_endpoint(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'qwen-plus'},
                {'id': 'wanx-image'},
            ]
        }
        mock_get.return_value = mock_response

        response = self.client.post('/api/v1/models/providers/discover_vendor_models/', {
            'vendor': 'dashscope',
            'capability': 'llm',
            'api_key': 'sk-test',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['capability'], 'llm')
        self.assertEqual([item['id'] for item in response.data['models']], ['qwen-plus', 'wanx-image'])
        self.assertTrue(response.data['models'][0]['is_capability_match'])
        self.assertEqual(response.data['models'][1]['classified_capability'], 'text2image')

    def test_batch_create_vendor_models_endpoint(self):
        response = self.client.post('/api/v1/models/providers/batch_create_vendor_models/', {
            'vendor': 'moonshot',
            'capability': 'llm',
            'api_key': 'sk-test',
            'model_names': ['moonshot-v1-8k'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_count'], 1)
        self.assertEqual(response.data['capability'], 'llm')
        self.assertTrue(ModelProvider.objects.filter(model_name='moonshot-v1-8k').exists())

    def test_discover_vendor_models_rejects_unsupported_capability(self):
        response = self.client.post('/api/v1/models/providers/discover_vendor_models/', {
            'vendor': 'moonshot',
            'capability': 'image2video',
            'api_key': 'sk-test',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('capability', response.data)

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_supports_newapi_custom_url(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o-mini'},
            ]
        }
        mock_get.return_value = mock_response

        response = self.client.post('/api/v1/models/providers/discover_vendor_models/', {
            'vendor': 'newapi',
            'capability': 'llm',
            'api_key': 'sk-test',
            'api_url': 'https://newapi.example.com/v1/chat/completions',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_url'], 'https://newapi.example.com/v1/chat/completions')

    def test_batch_create_vendor_models_supports_newapi_llm(self):
        response = self.client.post('/api/v1/models/providers/batch_create_vendor_models/', {
            'vendor': 'newapi',
            'capability': 'llm',
            'api_key': 'sk-test',
            'api_url': 'https://newapi.example.com/v1/chat/completions',
            'model_names': ['gpt-4o-mini'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider = ModelProvider.objects.get(model_name='gpt-4o-mini')
        self.assertEqual(provider.api_url, 'https://newapi.example.com/v1/chat/completions')
        self.assertEqual(provider.extra_config.get('vendor'), 'newapi')


    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_supports_builtin_custom_url(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4.1-mini'},
            ]
        }
        mock_get.return_value = mock_response

        response = self.client.post('/api/v1/models/providers/discover_vendor_models/', {
            'vendor': 'openai',
            'capability': 'llm',
            'api_key': 'sk-test',
            'api_url': 'https://gateway.example.com/v1/chat/completions',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_url'], 'https://gateway.example.com/v1/chat/completions')

    def test_batch_create_vendor_models_supports_newapi_text2image(self):
        response = self.client.post('/api/v1/models/providers/batch_create_vendor_models/', {
            'vendor': 'newapi',
            'capability': 'text2image',
            'api_key': 'sk-test',
            'api_url': 'https://newapi.example.com/v1/images/generations',
            'model_names': ['flux-dev'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider = ModelProvider.objects.get(model_name='flux-dev')
        self.assertEqual(provider.provider_type, 'text2image')
        self.assertEqual(provider.api_url, 'https://newapi.example.com/v1/images/generations')

    def test_batch_create_vendor_models_supports_newapi_image2video(self):
        response = self.client.post('/api/v1/models/providers/batch_create_vendor_models/', {
            'vendor': 'newapi',
            'capability': 'image2video',
            'api_key': 'sk-test',
            'api_url': 'https://newapi.example.com/v1/videos/generations',
            'model_names': ['kling-v1'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider = ModelProvider.objects.get(model_name='kling-v1')
        self.assertEqual(provider.provider_type, 'image2video')
        self.assertEqual(provider.api_url, 'https://newapi.example.com/v1/videos/generations')

    def test_vendor_connection_config_get_returns_saved_config(self):
        VendorConnectionConfig.objects.create(
            user=self.user,
            vendor='openai',
            capability='llm',
            api_key='sk-saved',
            api_url='https://gateway.example.com/v1/chat/completions',
        )

        response = self.client.get('/api/v1/models/providers/vendor_connection_config/', {
            'vendor': 'openai',
            'capability': 'llm',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['api_key'], 'sk-saved')
        self.assertEqual(response.data['api_url'], 'https://gateway.example.com/v1/chat/completions')

    def test_vendor_connection_config_put_persists_api_key_and_url(self):
        response = self.client.put('/api/v1/models/providers/vendor_connection_config/', {
            'vendor': 'openai',
            'capability': 'llm',
            'api_key': 'sk-put',
            'api_url': 'https://gateway.example.com/v1/chat/completions',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        config = VendorConnectionConfig.objects.get(user=self.user, vendor='openai', capability='llm')
        self.assertEqual(config.api_key, 'sk-put')
        self.assertEqual(config.api_url, 'https://gateway.example.com/v1/chat/completions')

    @patch('apps.models.services.requests.get')
    def test_discover_vendor_models_persists_vendor_connection_config(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 'gpt-4o-mini'},
            ]
        }
        mock_get.return_value = mock_response

        response = self.client.post('/api/v1/models/providers/discover_vendor_models/', {
            'vendor': 'openai',
            'capability': 'llm',
            'api_key': 'sk-discover',
            'api_url': 'https://gateway.example.com/v1/chat/completions',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        config = VendorConnectionConfig.objects.get(user=self.user, vendor='openai', capability='llm')
        self.assertEqual(config.api_key, 'sk-discover')
        self.assertEqual(config.api_url, 'https://gateway.example.com/v1/chat/completions')

    def test_batch_create_vendor_models_persists_vendor_connection_config(self):
        response = self.client.post('/api/v1/models/providers/batch_create_vendor_models/', {
            'vendor': 'moonshot',
            'capability': 'llm',
            'api_key': 'sk-batch',
            'api_url': 'https://api.moonshot.cn/v1/chat/completions',
            'model_names': ['moonshot-v1-8k'],
            'is_active': True,
            'timeout': 60,
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 1.0,
            'rate_limit_rpm': 60,
            'rate_limit_rpd': 1000,
            'priority': 0,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        config = VendorConnectionConfig.objects.get(user=self.user, vendor='moonshot', capability='llm')
        self.assertEqual(config.api_key, 'sk-batch')
        self.assertEqual(config.api_url, 'https://api.moonshot.cn/v1/chat/completions')
