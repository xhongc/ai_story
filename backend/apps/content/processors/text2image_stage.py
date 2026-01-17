"""
文生图阶段处理器
职责: 为每个分镜生成图片
遵循单一职责原则(SRP) + 开闭原则(OCP)
"""

import copy
import logging
import random
from typing import Any, Dict, Generator, List, Optional
from jinja2 import Template, TemplateError

from core.ai_client.factory import create_ai_client
from core.pipeline.base import PipelineContext, StageProcessor
from django.utils import timezone

from apps.content.models import GeneratedImage, Storyboard
from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectStage

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
        storyboard_ids: List[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        pass

    def process_stream(
        self,
        project_id: str,
        storyboard_ids: List[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行文生图生成
        用于SSE实时推送进度

        Args:
            project_id: 项目ID
            storyboard_ids: 指定要生成的分镜ID列表(可选,默认生成所有)

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

            storyboards_query = StoryboardModel.objects.filter(project=project).order_by('sequence_number')

            # 如果指定了分镜ID,则只处理这些分镜
            if storyboard_ids:
                storyboards_query = storyboards_query.filter(sequence_number__in=storyboard_ids)

            storyboards = list(storyboards_query)

            if not storyboards:
                yield {
                    'type': 'error',
                    'error': '没有找到分镜数据'
                }
                return

            total = len(storyboards)
            yield {
                'type': 'info',
                'message': f'开始生成图片，共 {total} 个分镜...'
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
            output_data = {
                'total_storyboards': total,
                'success_count': generated_count,
                'failed_count': failed_count
            }

            stage.output_data = output_data
            stage.status = 'completed' if failed_count == 0 else 'completed'
            stage.completed_at = timezone.now()
            stage.save()

            yield {
                'type': 'done',
                'message': f'图片生成完成: 成功 {generated_count}/{total}',
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
        # 1. 优先从项目模型配置获取
        config = getattr(project, 'model_config', None)

        if config:
            providers = list(config.image_providers.all())

            if providers:
                # 简化版: 使用第一个提供商
                # TODO: 实现负载均衡策略
                return providers[0]

        # 2. 获取系统默认提供商
        provider = ModelProvider.objects.filter(
            provider_type='text2image',
            is_active=True
        ).first()

        if not provider:
            raise Exception("未找到可用的文生图模型提供商，请在后台配置")

        return provider
        
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
        from apps.prompts.models import GlobalVariable

        # 获取项目创建者的全局变量
        user = project.user
        variables = GlobalVariable.get_variables_for_user(
            user=user,
            include_system=True
        )

        return variables

    def _get_global_variables_sync(self, project: Project) -> Dict[str, Any]:
        """
        同步获取全局变量（用于非异步上下文）
        """
        return self._get_global_variables(project)

    def _build_prompt(self, project: Project, storyboard: dict) -> str:
        """
        构建提示词
        从PromptTemplate获取模板并使用Jinja2渲染
        支持全局变量注入
        """
        template = self._get_prompt_template(project)

        if not template:
            raise ValueError(f"未找到 {self.stage_type} 阶段的提示词模板")

        try:
            # 获取全局变量（同步方式）
            global_vars = self._get_global_variables_sync(project)

            # 准备模板变量（优先级：storyboard > project > global_vars）
            template_vars = {
                **global_vars,  # 全局变量（最低优先级）
                "random_seed": random.randint(1, 1000000),
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **storyboard  # 合并输入数据作为变量（最高优先级）
            }

            # 渲染Jinja2模板
            jinja_template = Template(template.template_content)
            rendered_prompt = jinja_template.render(**template_vars)

            return rendered_prompt

        except TemplateError as e:
            logger.error(f"提示词模板渲染失败: {str(e)}")
            raise ValueError(f"提示词模板渲染失败: {str(e)}")
            
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
            prompt = self._build_prompt(project, storyboard)
            model_name = provider.model_name
            api_key = provider.api_key
            api_url = provider.api_url
            generation_params = {
                'model': model_name,
                'prompt': prompt,
                'ratio': ratio,
                'resolution': resolution
            }
            client = create_ai_client(provider)
            # 调用generate (同步函数)
            response = client.generate(
                api_url=api_url,
                session_id=api_key,
                model=model_name,
                prompt=prompt,
                ratio=ratio,
                resolution=resolution
            )

            if not response:
                logger.error(f"分镜 {storyboard.get('sequence_number')} 图片生成返回空结果")
                return None

            # 解析响应
            # 假设响应格式: {"data": [{"url": "...", "width": 1920, "height": 1080}]}
            if 'data' not in response or not response['data']:
                logger.error(f"分镜 {storyboard.get('sequence_number')} 响应格式错误: {response}")
                return None
            # [{"url": "http://"}]
            image_data = response['data']

            return image_data

        except Exception as e:
            logger.error(f"分镜 {storyboard.get('sequence_number')} 图片生成异常: {str(e)}", exc_info=True)

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
