import base64
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.content.processors.text2image_stage import Text2ImageStageProcessor
from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectAssetBinding, Series
from apps.prompts.models import GlobalVariable, PromptTemplate, PromptTemplateSet


User = get_user_model()

TINY_PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9pG2N3sAAAAASUVORK5CYII='
)


class Text2ImageAssetPromptTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='image-asset-user', password='secret123')
        self.series = Series.objects.create(name='资产测试系列', description='测试', user=self.user)
        self.project = Project.objects.create(
            user=self.user,
            series=self.series,
            episode_number=1,
            sort_order=1,
            episode_title='第1集',
            name='资产文生图项目',
            original_topic='测试图片资产替换',
        )
        self.provider = ModelProvider.objects.create(
            name='火山文生图',
            provider_type='text2image',
            api_url='https://ark.cn-beijing.volces.com/api/v3/images/generations',
            api_key='test-key',
            model_name='doubao-seedream-5-0-250428',
            executor_class='core.ai_client.text2image_client.Text2ImageClient',
            extra_config={'width': 1024, 'height': 1024},
        )
        self.template_set = PromptTemplateSet.objects.create(
            name='测试提示词集',
            description='测试',
            created_by=self.user,
        )
        self.project.prompt_template_set = self.template_set
        self.project.save(update_fields=['prompt_template_set', 'updated_at'])

        PromptTemplate.objects.create(
            template_set=self.template_set,
            stage_type='image_generation',
            model_provider=self.provider,
            template_content='{{ visual_prompt }}',
            variables={'visual_prompt': 'string'},
            client_params={'ratio': '16:9', 'steps': 32, 'negative_prompt': '低质量'},
            is_active=True,
        )

        self.hero_asset = GlobalVariable.objects.create(
            key='hero_asset',
            value='女孩参考图',
            variable_type='image',
            scope='user',
            created_by=self.user,
            image_file=SimpleUploadedFile('hero.png', TINY_PNG_BYTES, content_type='image/png'),
        )
        self.cow_asset = GlobalVariable.objects.create(
            key='cow_asset',
            value='奶牛玩偶参考图',
            variable_type='image',
            scope='user',
            created_by=self.user,
            image_file=SimpleUploadedFile('cow.png', TINY_PNG_BYTES, content_type='image/png'),
        )
        ProjectAssetBinding.objects.create(project=self.project, asset=self.hero_asset)
        ProjectAssetBinding.objects.create(project=self.project, asset=self.cow_asset)

    @patch('apps.content.processors.text2image_stage.create_ai_client')
    def test_generate_single_image_replaces_image_assets_with_labels_and_base64(self, mock_create_ai_client):
        client = mock_create_ai_client.return_value
        client.generate.return_value = SimpleNamespace(
            data=[{'url': 'https://example.com/generated.png', 'width': 1024, 'height': 1024}],
            error=None,
        )

        processor = Text2ImageStageProcessor()
        storyboard = {
            'scene_number': 1,
            'narration': '女孩和奶牛玩偶在游乐园',
            'visual_prompt': '请参考{{ hero_asset }}和{{ cow_asset }}，并再次强调{{ hero_asset }}',
            'shot_type': '中景',
        }

        result = processor._generate_single_image(self.project, storyboard, self.provider)

        self.assertEqual(len(result), 1)
        generate_kwargs = client.generate.call_args.kwargs
        self.assertEqual(generate_kwargs['prompt'], '请参考图1和图2，并再次强调图1')
        self.assertEqual(len(generate_kwargs['image']), 2)
        self.assertTrue(generate_kwargs['image'][0].startswith('data:image/png;base64,'))
        self.assertTrue(generate_kwargs['image'][1].startswith('data:image/png;base64,'))
        self.assertEqual(generate_kwargs['ratio'], '16:9')
        self.assertEqual(generate_kwargs['steps'], 32)
        self.assertEqual(generate_kwargs['negative_prompt'], '低质量')
