"""
文生图阶段处理器
职责: 为每个分镜生成图片
遵循单一职责原则(SRP) + 开闭原则(OCP)
"""

import base64
import copy
import logging
import mimetypes
import random
import re
from collections.abc import Mapping
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests
from django.conf import settings
from jinja2 import Template, TemplateError

from core.ai_client.factory import create_ai_client
from core.pipeline.base import PipelineContext, StageProcessor
from django.utils import timezone

from apps.content.models import GeneratedImage, Storyboard
from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectStage
from apps.prompts.client_param_resolver import resolve_stage_client_params

logger = logging.getLogger(__name__)


class Text2ImageStageProcessor(StageProcessor):
    """
    文生图阶段处理器

    职责:
    - 读取storyboard阶段的分镜数据
    - 为每个分镜调用generate生成图片
    - 保存生成的图片到GeneratedImage模型
    - 支持批量生成和流式进度推送

    特性:
    - 并发生成多个图片(可配置并发数)
    - 失败自动重试机制
    - 支持流式进度更新
    """

    def __init__(self):
        """初始化处理器"""
        super().__init__('image_generation')
        self.stage_type = 'image_generation'
        self.max_concurrent = 3  # 最大并发生成数
        self._image_asset_token_pattern = re.compile(r'__IMAGE_ASSET_(\d+)__')

    async def validate(self, context: PipelineContext) -> bool:
        """
        验证是否可以执行文生图阶段

        检查:
        1. 项目是否存在
        2. storyboard阶段是否已完成
        3. 是否有分镜数据
        4. 是否配置了文生图模型
        """
        try:
            project = Project.objects.get(id=context.project_id)

            # 检查storyboard阶段是否完成
            storyboard_stage = ProjectStage.objects.filter(
                project=project,
                stage_type='storyboard',
                status='completed'
            ).first()

            if not storyboard_stage:
                logger.error(f"项目 {context.project_id} 的storyboard阶段未完成")
                return False

            # 检查是否有分镜数据
            storyboards_count = Storyboard.objects.filter(project=project).count()

            if storyboards_count == 0:
                logger.error(f"项目 {context.project_id} 没有分镜数据")
                return False

            # 检查是否有可用的文生图模型
            provider = await self._get_text2image_provider(project)
            if not provider:
                logger.error(f"项目 {context.project_id} 未配置文生图模型")
                return False

            return True

        except Project.DoesNotExist:
            logger.error(f"项目 {context.project_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"验证失败: {str(e)}", exc_info=True)
            return False

    def process(
        self,
        project_id: str,
        storyboard_ids: List[str] = None,
        force_regenerate: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        pass

    def process_stream(
        self,
        project_id: str,
        storyboard_ids: List[str] = None,
        force_regenerate: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行文生图生成
        用于SSE实时推送进度

        Args:
            project_id: 项目ID
            storyboard_ids: 指定要生成的分镜ID列表(可选,默认生成所有)
            force_regenerate: 是否强制重生成已完成分镜

        Yields:
            Dict包含: type (progress/image_generated/done/error), content, data
        """
        stage = None
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=project_id)
            stage, created = ProjectStage.objects.get_or_create(
                project=project,
                stage_type=self.stage_type
            )

            # 更新阶段状态
            stage.status = 'processing'
            stage.started_at = timezone.now()
            stage.save()

            yield {
                'type': 'stage_update',
                'stage': {
                    'id': str(stage.id),
                    'status': 'processing',
                    'stage_type': self.stage_type,
                    'started_at': stage.started_at.isoformat()
                }
            }

            # 从 Storyboard 模型获取分镜列表
            from apps.content.models import Storyboard as StoryboardModel

            all_storyboards_query = StoryboardModel.objects.filter(project=project).order_by('sequence_number')
            target_storyboards_query = all_storyboards_query

            # 如果指定了分镜ID,则只处理这些分镜
            if storyboard_ids:
                target_storyboards_query = target_storyboards_query.filter(id__in=storyboard_ids)

            total_storyboards = all_storyboards_query.count()
            target_storyboards_count = target_storyboards_query.count()

            if target_storyboards_count == 0:
                yield {
                    'type': 'error',
                    'error': '没有找到分镜数据'
                }
                return

            completed_storyboard_ids = set(
                GeneratedImage.objects.filter(
                    storyboard__project=project,
                    status='completed'
                ).values_list('storyboard_id', flat=True).distinct()
            )

            storyboards_query = target_storyboards_query
            if not force_regenerate:
                storyboards_query = storyboards_query.exclude(id__in=completed_storyboard_ids)
            storyboards = list(storyboards_query)
            skipped_count = target_storyboards_count - len(storyboards)

            if not storyboards:
                completed_storyboards = len(completed_storyboard_ids)
                failed_count = max(total_storyboards - completed_storyboards, 0)
                output_data = {
                    'total_storyboards': total_storyboards,
                    'success_count': completed_storyboards,
                    'failed_count': failed_count,
                    'generated_count': 0,
                    'skipped_count': skipped_count,
                }

                stage.output_data = output_data
                stage.status = 'completed' if failed_count == 0 else 'failed'
                stage.error_message = '' if failed_count == 0 else '仍有分镜图片未生成完成'
                stage.completed_at = timezone.now()
                stage.save()

                yield {
                    'type': 'done',
                    'message': f'图片生成完成: 已完成 {completed_storyboards}/{total_storyboards}',
                    'data': output_data,
                    'stage': {
                        'id': str(stage.id),
                        'status': stage.status,
                        'output_data': output_data,
                        'completed_at': stage.completed_at.isoformat() if stage.completed_at else ''
                    }
                }
                return

            total = len(storyboards)
            yield {
                'type': 'info',
                'message': f'开始生成图片，待处理 {total} 个分镜...'
            }

            # 获取AI客户端配置
            provider = self._get_text2image_provider(project)

            # 批量生成图片
            generated_count = 0
            failed_count = 0

            for index, storyboard_obj in enumerate(storyboards, 1):
                try:
                    # 构建分镜数据字典(兼容原有接口)
                    storyboard_dict = {
                        'scene_number': storyboard_obj.sequence_number,
                        'narration': storyboard_obj.narration_text,
                        'visual_prompt': storyboard_obj.image_prompt,
                        'shot_type': storyboard_obj.scene_description
                    }

                    # 进度更新
                    yield {
                        'type': 'progress',
                        'current': index,
                        'total': total,
                        'message': f'正在生成第 {index}/{total} 张图片...',
                        'storyboard': storyboard_dict
                    }

                    # 生成图片
                    result = self._generate_single_image(
                        project=project,
                        storyboard=storyboard_dict,
                        provider=provider
                    )

                    if result:
                        generated_count += 1

                        # 保存结果到 GeneratedImage 模型
                        self._save_result(
                            project=project,
                            stage=stage,
                            storyboard=storyboard_dict,
                            result=result
                        )

                        # 图片生成成功
                        yield {
                            'type': 'image_generated',
                            'storyboard_id': storyboard_obj.sequence_number,
                            'sequence_number': storyboard_obj.sequence_number,
                        }
                    else:
                        failed_count += 1
                        yield {
                            'type': 'warning',
                            'message': f'分镜 {storyboard_obj.sequence_number} 图片生成失败'
                        }

                except Exception as e:
                    failed_count += 1
                    logger.error(f"分镜 {index} 生成失败: {str(e)}")
                    yield {
                        'type': 'error',
                        'error': f'分镜 {index} 生成失败: {str(e)}',
                        'storyboard_id': str(storyboard_obj.sequence_number)
                    }

            # 保存最终结果到阶段
            completed_storyboards = GeneratedImage.objects.filter(
                storyboard__project=project,
                status='completed'
            ).values('storyboard_id').distinct().count()
            project_failed_count = max(total_storyboards - completed_storyboards, 0)

            output_data = {
                'total_storyboards': total_storyboards,
                'success_count': completed_storyboards,
                'failed_count': project_failed_count,
                'generated_count': generated_count,
                'skipped_count': skipped_count,
            }

            stage.output_data = output_data
            stage.status = 'completed' if project_failed_count == 0 else 'failed'
            stage.error_message = '' if project_failed_count == 0 else '仍有分镜图片未生成完成'
            stage.completed_at = timezone.now()
            stage.save()

            yield {
                'type': 'done',
                'message': f'图片生成完成: 已完成 {completed_storyboards}/{total_storyboards}',
                'data': output_data,
                'stage': {
                    'id': str(stage.id),
                    'status': stage.status,
                    'output_data': output_data,
                    'completed_at': stage.completed_at.isoformat() if stage.completed_at else ''
                }
            }

        except Exception as e:
            logger.error(f"流式文生图处理失败: {str(e)}", exc_info=True)

            # 更新阶段状态
            if stage:
                try:
                    stage.status = 'failed'
                    stage.error_message = str(e)
                    stage.save()
                except Exception:
                    pass

            yield {
                'type': 'error',
                'error': str(e)
            }

    def on_failure(self, context: PipelineContext, error: Exception):
        """失败处理"""
        try:
            project = Project.objects.get(id=context.project_id)
            stage = ProjectStage.objects.filter(
                project=project,
                stage_type=self.stage_type
            ).first()

            if stage:
                stage.status = 'failed'
                stage.error_message = str(error)
                stage.save()

        except Exception as e:
            logger.error(f"更新失败状态失败: {str(e)}")

    # ===== 私有辅助方法 =====

    def _save_result(
        self,
        project: Project,
        stage: ProjectStage,
        storyboard: dict,
        result: List[Dict[str, Any]]
    ) -> None:
        """
        保存图片生成结果到 GeneratedImage 模型

        Args:
            project: 项目对象
            stage: 当前阶段对象(image_generation)
            storyboard: 分镜数据字典
            result: 生成的图片URL列表 [{"url": "...", "width": 1920, "height": 1080}]
        """
        from apps.content.models import Storyboard as StoryboardModel, GeneratedImage

        # 获取对应的 Storyboard 模型实例
        scene_number = storyboard.get('scene_number')
        storyboard_obj = StoryboardModel.objects.filter(
            project=project,
            sequence_number=scene_number
        ).first()

        if not storyboard_obj:
            logger.error(f"未找到序号为 {scene_number} 的分镜对象")
            return

        # 获取模型提供商
        provider = self._get_text2image_provider(project)

        # 保存每张生成的图片
        for image_data in result:
            image_url = image_data.get('url', '')
            width = image_data.get('width', 0)
            height = image_data.get('height', 0)

            GeneratedImage.objects.create(
                storyboard=storyboard_obj,
                image_url=image_url,
                thumbnail_url='',
                generation_params={
                    'prompt': storyboard.get('visual_prompt', ''),
                    'model': provider.model_name if provider else '',
                    'original_data': image_data
                },
                model_provider=provider,
                status='completed',
                width=width,
                height=height,
                file_size=0  # 如果API返回了文件大小,可以在这里设置
            )

    def _get_text2image_provider(self, project: Project) -> Optional[ModelProvider]:
        """获取文生图模型提供商"""

        # 1. 从提示词模板获取默认模型
        template = self._get_prompt_template(project)
        if template and template.model_provider:
            return template.model_provider


        return None
        
    def _get_prompt_template(self, project: Project):
        """获取提示词模板"""
        # 从项目的prompt_template_set中获取
        template_set = getattr(project, 'prompt_template_set', None)
        from apps.prompts.models import PromptTemplateSet, PromptTemplate

        if not template_set:
            # 尝试获取默认提示词集
            template_set = PromptTemplateSet.objects.filter(is_default=True).first()

        if not template_set:
            return None
        # 获取对应阶段的模板 - 使用select_related预加载model_provider
        template = PromptTemplate.objects.select_related('model_provider').filter(
            template_set=template_set,
            stage_type=self.stage_type,
            is_active=True
        ).first()

        return template

    def _get_global_variables(self, project: Project) -> Dict[str, Any]:
        """
        获取全局变量
        包括用户级和系统级变量
        """
        from apps.projects.asset_context import build_project_asset_context

        return build_project_asset_context(project)

    def _get_global_variables_sync(self, project: Project) -> Dict[str, Any]:
        """
        同步获取全局变量（用于非异步上下文）
        """
        return self._get_global_variables(project)

    def replace_double_quote_in_dict(self, d):
        """
        递归替换字典中所有字符串类型value里的双引号为单引号
        支持嵌套字典、列表等复杂结构
        """
        # 如果是字典，遍历所有键值对
        if isinstance(d, dict):
            for key, value in d.items():
                d[key] = self.replace_double_quote_in_dict(value)

        # 如果是列表/元组，遍历每个元素
        elif isinstance(d, (list, tuple)):
            # 列表直接生成新列表，元组转列表处理后转回元组
            if isinstance(d, list):
                return [self.replace_double_quote_in_dict(item) for item in d]
            else:
                return tuple([self.replace_double_quote_in_dict(item) for item in d])
        # 如果是字符串，替换双引号为单引号
        elif isinstance(d, str):
            return d.replace('"', "'")
        # 非字符串/容器类型（数字、布尔等）直接返回
        else:
            return d

    def _get_accessible_image_assets(self, project: Project) -> Dict[str, Any]:
        """获取当前项目可用的图片资产映射。"""
        from django.db.models import Q

        from apps.prompts.models import GlobalVariable

        image_assets: Dict[str, Any] = {}

        bindings = project.asset_bindings.select_related('asset').all()
        for binding in bindings:
            asset = binding.asset
            if not asset or not asset.is_active or asset.variable_type != 'image':
                continue
            image_assets[asset.key] = asset

        query = (
            Q(created_by=project.user, scope='user', is_active=True, variable_type='image')
            | Q(scope='system', is_active=True, variable_type='image')
        )
        for asset in GlobalVariable.objects.filter(query).order_by('scope', 'group', 'key'):
            image_assets.setdefault(asset.key, asset)

        return image_assets

    def _build_image_asset_tokens(self, image_assets: Dict[str, Any]) -> Dict[str, str]:
        """为图片资产生成模板渲染占位符。"""
        return {
            asset_key: f'__IMAGE_ASSET_{index}__'
            for index, asset_key in enumerate(image_assets.keys(), 1)
        }

    def _inject_image_asset_tokens(
        self,
        template_vars: Dict[str, Any],
        token_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """将图片资产在模板上下文中替换为内部占位符。"""
        injected_vars = copy.deepcopy(template_vars)

        for asset_key, token in token_map.items():
            if asset_key in injected_vars:
                injected_vars[asset_key] = token

        project_assets = injected_vars.get('project_assets')
        if isinstance(project_assets, dict):
            for asset_key, token in token_map.items():
                if asset_key in project_assets:
                    project_assets[asset_key] = token

        asset_bindings = injected_vars.get('asset_bindings')
        if isinstance(asset_bindings, list):
            for binding in asset_bindings:
                if not isinstance(binding, dict):
                    continue
                asset_key = binding.get('key')
                if binding.get('variable_type') != 'image' or asset_key not in token_map:
                    continue
                token = token_map[asset_key]
                binding['typed_value'] = token
                binding['prompt_text'] = token

        return injected_vars

    def _render_template_recursively(
        self,
        template_content: str,
        template_vars: Dict[str, Any],
        max_passes: int = 3,
    ) -> str:
        """支持对嵌套模板字符串进行有限次递归渲染。"""
        rendered = template_content
        for _ in range(max_passes):
            next_rendered = Template(rendered).render(**template_vars)
            if next_rendered == rendered:
                return next_rendered
            rendered = next_rendered
            if '{{' not in rendered and '{%' not in rendered:
                return rendered
        return rendered

    def _guess_image_mime_type(self, filename: str = '', image_bytes: bytes = b'') -> str:
        """根据文件名或二进制头推断图片 MIME。"""
        if filename:
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type and guessed_type.startswith('image/'):
                return guessed_type.lower()

        if image_bytes.startswith(b'\xFF\xD8\xFF'):
            return 'image/jpeg'
        if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if image_bytes.startswith((b'GIF87a', b'GIF89a')):
            return 'image/gif'
        if image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:16]:
            return 'image/webp'
        if image_bytes.startswith(b'BM'):
            return 'image/bmp'
        if image_bytes.lstrip().startswith(b'<svg'):
            return 'image/svg+xml'

        return 'image/png'

    def _read_image_asset_bytes(self, asset) -> Tuple[bytes, str]:
        """读取图片资产原始字节并返回 MIME 类型。"""
        data_uri = (asset.value or '').strip()
        if data_uri.startswith('data:image/') and ';base64,' in data_uri:
            header, encoded = data_uri.split(';base64,', 1)
            return base64.b64decode(encoded), header[5:].lower()

        if asset.image_file:
            image_bytes = asset.image_file.read()
            asset.image_file.seek(0)
            return image_bytes, self._guess_image_mime_type(asset.image_file.name, image_bytes)

        source = str(asset.get_typed_value() or asset.value or '').strip()
        if not source:
            raise ValueError(f'图片资产 {asset.key} 缺少可用图片内容')

        if source.startswith('/api/v1/content/storage/image/'):
            relative_path = source.split('/api/v1/content/storage/image/', 1)[1]
            image_path = settings.STORAGE_ROOT / 'image' / relative_path
            image_bytes = image_path.read_bytes()
            return image_bytes, self._guess_image_mime_type(image_path.name, image_bytes)

        normalized_media_url = f'/{str(settings.MEDIA_URL).strip("/")}/'
        if source.startswith(normalized_media_url) or source.startswith(str(settings.MEDIA_URL)):
            relative_path = source.split(str(settings.MEDIA_URL).strip('/'), 1)[-1].lstrip('/')
            image_path = settings.MEDIA_ROOT / relative_path
            image_bytes = image_path.read_bytes()
            return image_bytes, self._guess_image_mime_type(image_path.name, image_bytes)

        response = requests.get(source, timeout=30)
        response.raise_for_status()
        image_bytes = response.content
        content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        mime_type = content_type if content_type.startswith('image/') else self._guess_image_mime_type(source, image_bytes)
        return image_bytes, mime_type

    def _image_asset_to_data_uri(self, asset) -> str:
        """将图片资产转换为模型可直接消费的 data URI。"""
        raw_value = str(asset.value or '').strip()
        if raw_value.startswith('data:image/') and ';base64,' in raw_value:
            return raw_value

        image_bytes, mime_type = self._read_image_asset_bytes(asset)
        encoded = base64.b64encode(image_bytes).decode('utf-8')
        return f'data:{mime_type.lower()};base64,{encoded}'

    def _replace_image_asset_tokens(
        self,
        rendered_prompt: str,
        image_assets: Dict[str, Any],
        token_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """按图片在提示词中的出现顺序映射为 图1、图2，并构造 image 参数。"""
        ordered_tokens = []
        seen_tokens = set()

        for match in self._image_asset_token_pattern.finditer(rendered_prompt):
            token = match.group(0)
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
            ordered_tokens.append(token)

        if not ordered_tokens:
            return {
                'prompt': rendered_prompt,
                'image': [],
            }

        token_to_asset = {
            token: image_assets[asset_key]
            for asset_key, token in token_map.items()
        }
        token_to_label = {
            token: f'图{index}'
            for index, token in enumerate(ordered_tokens, 1)
        }

        final_prompt = rendered_prompt
        for token, label in token_to_label.items():
            final_prompt = final_prompt.replace(token, label)

        return {
            'prompt': final_prompt,
            'image': [self._image_asset_to_data_uri(token_to_asset[token]) for token in ordered_tokens],
        }

    def _build_generation_prompt_payload(self, project: Project, storyboard: dict) -> Dict[str, Any]:
        """构建最终文生图提示词及关联图片输入。"""
        template = self._get_prompt_template(project)

        if not template:
            raise ValueError(f"未找到 {self.stage_type} 阶段的提示词模板")

        try:
            global_vars = self._get_global_variables_sync(project)
            self.replace_double_quote_in_dict(storyboard)
            template_vars = {
                **global_vars,
                'random_seed': random.randint(1, 1000000),
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **storyboard,
            }

            image_assets = self._get_accessible_image_assets(project)
            token_map = self._build_image_asset_tokens(image_assets)
            injected_template_vars = self._inject_image_asset_tokens(template_vars, token_map)
            rendered_prompt = self._render_template_recursively(
                template.template_content,
                injected_template_vars,
            )
            return self._replace_image_asset_tokens(rendered_prompt, image_assets, token_map)

        except TemplateError as e:
            logger.error(f"提示词模板渲染失败: {str(e)}")
            raise ValueError(f"提示词模板渲染失败: {str(e)}")

    def _build_prompt(self, project: Project, storyboard: dict) -> str:
        """
        构建提示词
        从PromptTemplate获取模板并使用Jinja2渲染
        支持全局变量注入
        """
        return self._build_generation_prompt_payload(project, storyboard)['prompt']

    def _resolve_generation_client_params(
        self,
        project: Project,
        provider: ModelProvider,
        runtime_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template = self._get_prompt_template(project)
        return resolve_stage_client_params(
            self.stage_type,
            template=template,
            provider=provider,
            runtime_overrides=runtime_overrides or {},
        )
            
    def _generate_single_image(
        self,
        project: Project,
        storyboard: dict,
        provider: ModelProvider,
        ratio: str = "9:16",
        resolution: str = "2k"
    ) -> Optional[GeneratedImage]:
        """
        为单个分镜生成图片

        Args:
            storyboard: 分镜对象
            session_id: API会话ID
            model_name: 模型名称
            provider: 模型提供商
            ratio: 图片比例
            resolution: 分辨率

        Returns:
            GeneratedImage对象或None(失败时)
        """
        try:
            # 准备生成参数
            # 构建提示词
            prompt_payload = self._build_generation_prompt_payload(project, storyboard)
            prompt = prompt_payload['prompt']
            model_name = provider.model_name
            api_key = provider.api_key
            api_url = provider.api_url
            client_params = self._resolve_generation_client_params(
                project,
                provider,
                runtime_overrides={
                    'ratio': ratio,
                    'resolution': resolution,
                },
            )
            generation_params = {
                'model': model_name,
                'prompt': prompt,
                'image': prompt_payload['image'],
                'ratio': client_params.get('ratio', ratio),
                'resolution': client_params.get('resolution', resolution),
                'width': client_params.get('width', 1024),
                'height': client_params.get('height', 1024),
                'steps': client_params.get('steps', 20),
                'negative_prompt': client_params.get('negative_prompt', ''),
                'sample_count': client_params.get('sample_count', 1),
            }
            client = create_ai_client(provider)
            # 调用generate (同步函数)
            response = client.generate(
                api_url=api_url,
                session_id=api_key,
                model=model_name,
                prompt=prompt,
                image=prompt_payload['image'],
                ratio=client_params.get('ratio', ratio),
                resolution=client_params.get('resolution', resolution),
                height=client_params.get('height', 1024),
                width=client_params.get('width', 1024),
                steps=client_params.get('steps', 20),
                negative_prompt=client_params.get('negative_prompt', ''),
                sample_count=client_params.get('sample_count', 1),
            )

            if not response:
                logger.error(f"分镜 {storyboard.get('scene_number')} 图片生成返回空结果")
                return None

            # 解析响应
            # 兼容 AIResponse / dict / 其他映射对象
            response_data = None
            response_error = None

            if isinstance(response, Mapping):
                response_data = response.get('data')
                response_error = response.get('error')
            else:
                response_data = getattr(response, 'data', None)
                response_error = getattr(response, 'error', None)

            if not response_data:
                logger.error(
                    f"分镜 {storyboard.get('scene_number')} 响应格式错误: "
                    f"error={response_error}, response={response}"
                )
                return None

            if isinstance(response_data, Mapping):
                response_data = [response_data]
            elif not isinstance(response_data, list):
                logger.error(
                    f"分镜 {storyboard.get('scene_number')} 图片数据类型错误: "
                    f"{type(response_data).__name__}"
                )
                return None

            # [{"url": "http://"}]
            image_data = response_data

            return image_data

        except Exception as e:
            logger.error(f"分镜 {storyboard.get('scene_number')} 图片生成异常: {str(e)}", exc_info=True)

            # 创建失败记录
            try:
                GeneratedImage.objects.create(
                    storyboard=storyboard,
                    image_url='',
                    generation_params=generation_params,
                    model_provider=provider,
                    status='failed'
                )
            except:
                pass

            return None
