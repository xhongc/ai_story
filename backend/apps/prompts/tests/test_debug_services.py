import base64
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.models.models import ModelProvider
from apps.prompts.debug_services import PromptDebugService
from apps.prompts.models import GlobalVariable, PromptTemplate, PromptTemplateSet


User = get_user_model()

TINY_PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9pG2N3sAAAAASUVORK5CYII='
)


class PromptDebugServiceText2ImageTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='prompt-debug-user', password='secret123')
        self.provider = ModelProvider.objects.create(
            name='调试文生图模型',
            provider_type='text2image',
            api_url='https://ark.cn-beijing.volces.com/api/v3/images/generations',
            api_key='debug-key',
            model_name='doubao-seedream-5-0-250428',
            executor_class='core.ai_client.text2image_client.Text2ImageClient',
            extra_config={'width': 1024, 'height': 1024},
        )
        self.template_set = PromptTemplateSet.objects.create(
            name='调试提示词集',
            description='测试',
            created_by=self.user,
        )
        self.template = PromptTemplate.objects.create(
            template_set=self.template_set,
            stage_type='image_generation',
            model_provider=self.provider,
            template_content='{{ visual_prompt }}',
            variables={'visual_prompt': 'string'},
            client_params={'ratio': '9:16', 'steps': 28, 'negative_prompt': '模糊'},
            is_active=True,
        )
        self.session = PromptDebugService.get_or_create_session(self.template, self.user)

        GlobalVariable.objects.create(
            key='hero_asset',
            value='女孩参考图',
            variable_type='image',
            scope='user',
            created_by=self.user,
            image_file=SimpleUploadedFile('hero.png', TINY_PNG_BYTES, content_type='image/png'),
        )
        GlobalVariable.objects.create(
            key='cow_asset',
            value='奶牛玩偶参考图',
            variable_type='image',
            scope='user',
            created_by=self.user,
            image_file=SimpleUploadedFile('cow.png', TINY_PNG_BYTES, content_type='image/png'),
        )

    @patch('apps.prompts.debug_services.create_ai_client')
    def test_run_session_passes_labeled_prompt_and_base64_images(self, mock_create_ai_client):
        client = mock_create_ai_client.return_value
        client.generate.return_value = type('Response', (), {
            'success': True,
            'data': [{'url': 'https://example.com/generated.png'}],
            'metadata': {'latency_ms': 12},
        })()

        run = PromptDebugService.run_session(
            session=self.session,
            user=self.user,
            template_content='{{ visual_prompt }}',
            variable_values={
                'visual_prompt': '请参考{{ hero_asset }}和{{ cow_asset }}，并再次强调{{ hero_asset }}',
            },
            input_payload={},
            source_artifact_id=None,
            provider_id=str(self.provider.id),
        )

        generate_kwargs = client.generate.call_args.kwargs
        self.assertEqual(generate_kwargs['prompt'], '请参考图1和图2，并再次强调图1')
        self.assertEqual(len(generate_kwargs['image']), 2)
        self.assertTrue(generate_kwargs['image'][0].startswith('data:image/png;base64,'))
        self.assertTrue(generate_kwargs['image'][1].startswith('data:image/png;base64,'))
        self.assertEqual(generate_kwargs['ratio'], '9:16')
        self.assertEqual(generate_kwargs['steps'], 28)
        self.assertEqual(generate_kwargs['negative_prompt'], '模糊')
        self.assertEqual(run.rendered_prompt, '请参考图1和图2，并再次强调图1')
