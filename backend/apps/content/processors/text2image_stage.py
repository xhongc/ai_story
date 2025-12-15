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

            # 获取分镜列表
            try:
                if storyboard_ids:
                    storyboards = stage.output_data.get("human_text", {}).get("scenes", [])
                    storyboards = [i for i in storyboards if i["scene_number"] in storyboard_ids]
                else:
                    storyboards = stage.output_data.get("human_text", {}).get("scenes", [])
            except Exception as e:
                logger.error(f"获取分镜数据失败: {str(e)}", exc_info=True)
                yield {
                    'type': 'error',
                    'error': f'获取分镜数据失败: {str(e)}'
                }
                raise e

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
            generated_images = []
            failed_count = 0

            for index, storyboard in enumerate(storyboards, 1):
                try:
                    # 进度更新
                    yield {
                        'type': 'progress',
                        'current': index,
                        'total': total,
                        'message': f'正在生成第 {index}/{total} 张图片...',
                        'storyboard': storyboard
                    }

                    # 生成图片
                    result = self._generate_single_image(
                        project=project,
                        storyboard=storyboard,
                        provider=provider
                    )
                    # todo mock
                    # result = [{"url": "https://picsum.photos/200/300"}]
                    if result:
                        generated_images.append(result)

                        # 保存结果到当前阶段和video_generation阶段
                        self._save_result(
                            project=project,
                            stage=stage,
                            storyboard=storyboard,
                            result=result
                        )

                        # 图片生成成功
                        yield {
                            'type': 'image_generated',
                            'storyboard_id': storyboard["scene_number"],
                            'sequence_number': storyboard["scene_number"],
                        }
                    else:
                        failed_count += 1
                        yield {
                            'type': 'warning',
                            'message': f'分镜 {storyboard["scene_number"]} 图片生成失败'
                        }

                except Exception as e:
                    failed_count += 1
                    logger.error(f"分镜 {index} 生成失败: {str(e)}")
                    yield {
                        'type': 'error',
                        'error': f'分镜 {index} 生成失败: {str(e)}',
                        'storyboard_id': str(storyboard["scene_number"])
                    }

            # 保存最终结果
            success_count = len(generated_images)
            output_data = {
                'total_storyboards': total,
                'success_count': success_count,
                'failed_count': failed_count,
                'generated_image_ids': generated_images
            }

            yield {
                'type': 'done',
                'message': f'图片生成完成: 成功 {success_count}/{total}',
                'data': output_data,
                'stage': {
                    'id': str(stage.id),
                    'status': stage.status,
                    'output_data': output_data,
                    'completed_at': ''
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
        保存图片生成结果到当前阶段和video_generation阶段

        Args:
            project: 项目对象
            stage: 当前阶段对象(image_generation)
            storyboard: 分镜数据
            result: 生成的图片URL列表
        """
        # 保存到当前阶段(image_generation)
        # 使用深拷贝避免引用问题
        scenes = copy.deepcopy(stage.output_data.get("human_text", {}).get("scenes", []))
        for each in scenes:
            if each["scene_number"] == storyboard["scene_number"]:
                each["urls"] = result

        output_data = {
            "human_text": {
                "scenes": scenes
            }
        }

        # 使用 update() 方法确保数据库更新
        ProjectStage.objects.filter(id=stage.id).update(
            output_data=output_data
        )
        # 刷新本地对象
        stage.refresh_from_db()

        # 同步保存到图生视频阶段(video_generation)
        # 先读取现有数据，然后合并新的urls，避免覆盖其他字段
        video_stage = ProjectStage.objects.filter(
            project=project,
            stage_type="video_generation"
        ).first()

        if video_stage:
            # 深拷贝现有数据
            updated_input = copy.deepcopy(video_stage.input_data or {})
            updated_output = copy.deepcopy(video_stage.output_data or {})

            # 确保数据结构存在
            if "human_text" not in updated_input:
                updated_input["human_text"] = {}
            if "scenes" not in updated_input["human_text"]:
                updated_input["human_text"]["scenes"] = []

            if "human_text" not in updated_output:
                updated_output["human_text"] = {}
            if "scenes" not in updated_output["human_text"]:
                updated_output["human_text"]["scenes"] = []

            # 更新或添加场景的urls字段
            for data_dict in [updated_input, updated_output]:
                scenes_list = data_dict["human_text"]["scenes"]
                scene_found = False

                for scene in scenes_list:
                    if scene.get("scene_number") == storyboard["scene_number"]:
                        scene["urls"] = result
                        scene_found = True
                        break

                # 如果场景不存在，添加新场景
                if not scene_found:
                    new_scene = copy.deepcopy(storyboard)
                    new_scene["urls"] = result
                    scenes_list.append(new_scene)

            # 保存更新后的数据
            ProjectStage.objects.filter(id=video_stage.id).update(
                input_data=updated_input,
                output_data=updated_output
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

    async def _get_global_variables(self, project: Project) -> Dict[str, Any]:
        """
        获取全局变量
        包括用户级和系统级变量
        """
        from apps.prompts.models import GlobalVariable

        # 获取项目创建者的全局变量
        user = await project.created_by
        variables = await GlobalVariable.get_variables_for_user(
            user=user,
            include_system=True
        )

        return variables

    def _get_global_variables_sync(self, project: Project) -> Dict[str, Any]:
        """
        同步获取全局变量（用于非异步上下文）
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建新任务
                return asyncio.create_task(self._get_global_variables(project))
            else:
                return loop.run_until_complete(self._get_global_variables(project))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self._get_global_variables(project))

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
