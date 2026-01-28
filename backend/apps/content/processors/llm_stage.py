"""
通用LLM阶段处理器
职责: 处理所有基于LLM的处理阶段(文案改写、分镜生成、运镜生成)
遵循单一职责原则(SRP) + 开闭原则(OCP)
"""

import copy
import logging
from typing import Any, Dict, Generator, List, Optional
from core.pipeline.base import PipelineContext, StageProcessor, StageResult
from django.utils import timezone
from jinja2 import Template, TemplateError

from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectStage
from apps.prompts.models import PromptTemplate
from apps.projects.utils import parse_storyboard_json

logger = logging.getLogger(__name__)


class LLMStageProcessor(StageProcessor):
    """
    通用LLM阶段处理器
    可处理所有基于LLM的生成任务:
    - rewrite: 文案改写
    - storyboard: 分镜生成
    - camera_movement: 运镜生成

    特性:
    - 从ProjectStage读取输入数据
    - 从PromptTemplate读取提示词模板
    - 支持Jinja2模板渲染
    - 支持流式和非流式两种模式
    """

    def __init__(self, stage_type: str):
        """
        初始化处理器

        Args:
            stage_type: 阶段类型 ('rewrite'|'storyboard'|'camera_movement')
        """
        super().__init__(stage_type)
        self.stage_type = stage_type

    def validate(self, context: PipelineContext) -> bool:
        """
        验证是否可以执行该阶段
        检查:
        1. 项目是否存在
        2. 是否有提示词模板
        3. 前置阶段的输出数据是否就绪
        """
        try:
            project = Project.objects.get(id=context.project_id)

            # 检查是否有提示词模板
            template = self._get_prompt_template(project)
            if not template:
                logger.error(f"项目 {context.project_id} 缺少 {self.stage_type} 阶段的提示词模板")
                return False

            # 检查前置阶段数据
            stage = ProjectStage.objects.filter(
                project=project,
                stage_type=self.stage_type
            ).first()

            if stage and not stage.input_data:
                logger.warning(f"项目 {context.project_id} 的 {self.stage_type} 阶段缺少输入数据")
                # 对于第一个阶段(rewrite),允许从project.original_topic获取
                if self.stage_type != 'rewrite':
                    return False

            return True
        except Project.DoesNotExist:
            logger.error(f"项目 {context.project_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"验证失败: {str(e)}", exc_info=True)
            return False

    def process_stream(
        self,
        project_id: str,
        input_data: Dict[str, Any] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行LLM生成
        用于SSE实时推送

        Yields:
            Dict包含: type (token/done/error/stage_update), content, stage_data
        """
        stage = None
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=project_id)
            stage, created = ProjectStage.objects.get_or_create(
                project=project,
                stage_type=self.stage_type
            )

            # 获取输入数据(从领域模型读取)
            if not input_data:
                input_data = self._get_input_data(project, stage)

            # 更新阶段状态为运行中
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

            # 获取AI客户端
            ai_client = self._get_ai_client(project)

            # 构建提示词
            prompt = self._build_prompt(project, input_data)

            # 发送提示词信息
            yield {
                'type': 'info',
                'message': f'开始生成{self._get_stage_display_name()}...',
                'prompt_length': len(prompt)
            }

            # 根据阶段类型构建任务列表
            tasks = self._build_tasks(project, input_data)

            for index, task in enumerate(tasks, 1):
                # 流式生成
                full_text = ""
                for chunk in ai_client.generate_stream(
                    prompt=f'## 用户输入\n{task.get("user_prompt", "")}',
                    system_prompt=prompt,
                    max_tokens=self._get_max_tokens(),
                    temperature=self._get_temperature()
                ):
                    if chunk['type'] == 'token':
                        full_text = chunk['full_text']
                        print(chunk['content'], end="")
                        yield {
                            'type': 'token',
                            'content': chunk['content'],
                            'full_text': full_text
                        }

                    elif chunk['type'] == 'done':
                        # 保存结果到领域模型
                        self._save_result(
                            project, stage, full_text, prompt, {"index": task.get("scene_number", "")}
                        )

                        # 更新阶段状态
                        ProjectStage.objects.filter(id=stage.id).update(
                            completed_at=timezone.now(),
                            status='completed'
                        )

                    elif chunk['type'] == 'error':
                        # 更新阶段状态为失败
                        stage.status = 'failed'
                        stage.error_message = chunk['error']
                        stage.save()

                        yield {
                            'type': 'error',
                            'error': chunk['error'],
                            'stage': {
                                'id': str(stage.id),
                                'status': 'failed',
                                'error_message': chunk['error']
                            }
                        }

            yield {
                'type': 'done',
                'stage': {
                    'id': str(stage.id),
                    'status': 'completed',
                }
            }
        except Exception as e:
            logger.error(f"流式{self.stage_type}处理失败: {str(e)}", exc_info=True)

            # 更新阶段状态
            if stage:
                try:
                    stage.status = 'failed'
                    stage.error_message = str(e)
                    stage.save()
                except:
                    pass

            yield {
                'type': 'error',
                'error': str(e)
            }

    def _build_tasks(self, project: Project, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据阶段类型和输入数据构建任务列表

        Args:
            project: 项目对象
            input_data: 输入数据

        Returns:
            任务列表
        """
        from apps.content.models import Storyboard

        if self.stage_type == 'rewrite':
            # 文案改写: 单个任务
            return [{"user_prompt": input_data.get("raw_text", "")}]

        elif self.stage_type == 'storyboard':
            # 分镜生成: 单个任务
            return [{"user_prompt": input_data.get("raw_text", "")}]

        elif self.stage_type == 'camera_movement':
            # 运镜生成: 为每个分镜生成运镜
            storyboard_ids = input_data.get("storyboard_ids", [])

            # 从 Storyboard 模型获取分镜列表
            storyboards_query = Storyboard.objects.filter(project=project).order_by('sequence_number')

            if storyboard_ids:
                storyboards_query = storyboards_query.filter(id__in=storyboard_ids)

            storyboards = list(storyboards_query)

            tasks = []
            for sb in storyboards:
                tasks.append({
                    "user_prompt": f'剧本:{sb.narration_text}\n 画面: {sb.image_prompt}',
                    "scene_number": sb.sequence_number
                })

            return tasks

        else:
            return [{"user_prompt": str(input_data)}]

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

    def _get_input_data(self, project: Project, stage: ProjectStage) -> Dict[str, Any]:
        """
        获取输入数据
        从领域模型读取数据,而不是从 ProjectStage
        """
        from apps.content.models import ContentRewrite, Storyboard

        # 根据阶段类型获取输入数据
        if self.stage_type == 'rewrite':
            # 文案改写: 从项目的original_topic获取
            return {
                'raw_text': project.original_topic,
                'human_text': ''
            }

        elif self.stage_type == 'storyboard':
            # 分镜生成: 从 ContentRewrite 模型获取改写后的文本
            try:
                content_rewrite = ContentRewrite.objects.get(project=project)
                return {
                    'raw_text': content_rewrite.rewritten_text,
                    'human_text': ''
                }
            except ContentRewrite.DoesNotExist:
                raise ValueError("前置阶段(文案改写)未完成或无输出数据")

        elif self.stage_type == 'camera_movement':
            # 运镜生成: 从 Storyboard 模型获取分镜数据
            storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')

            if not storyboards.exists():
                raise ValueError("前置阶段(分镜生成)未完成或无输出数据")

            # 构建场景列表
            scenes = []
            for sb in storyboards:
                scenes.append({
                    'scene_number': sb.sequence_number,
                    'narration': sb.narration_text,
                    'visual_prompt': sb.image_prompt,
                    'shot_type': sb.scene_description
                })

            return {
                'human_text': {'scenes': scenes}
            }

        else:
            return {}

    def _get_prompt_template(self, project: Project) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        # 从项目的prompt_template_set中获取
        template_set = getattr(project, 'prompt_template_set', None)

        if not template_set:
            # 尝试获取默认提示词集
            from apps.prompts.models import PromptTemplateSet
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

    def _build_prompt(self, project: Project, input_data: Dict[str, Any]) -> str:
        """
        构建提示词
        从PromptTemplate获取模板并使用Jinja2渲染
        支持全局变量注入
        """
        template = self._get_prompt_template(project)

        if not template:
            raise ValueError(f"未找到 {self.stage_type} 阶段的提示词模板")

        try:
            # 获取全局变量
            global_vars = self._get_global_variables(project)

            # 准备模板变量（优先级：input_data > project > global_vars）
            template_vars = {
                **global_vars,  # 全局变量（最低优先级）
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **input_data  # 输入数据（最高优先级）
            }

            # 渲染Jinja2模板
            jinja_template = Template(template.template_content)
            rendered_prompt = jinja_template.render(**template_vars)

            return rendered_prompt

        except TemplateError as e:
            logger.error(f"提示词模板渲染失败: {str(e)}")
            raise ValueError(f"提示词模板渲染失败: {str(e)}")

    def _get_ai_client(self, project: Project):
        """获取AI客户端（使用动态执行器）"""
        from core.ai_client.factory import create_ai_client

        # 获取项目模型配置
        config = getattr(project, 'model_config', None)

        provider = None

        if config:
            # 根据阶段类型获取对应的模型提供商
            provider_field_map = {
                'rewrite': 'rewrite_providers',
                'storyboard': 'storyboard_providers',
                'camera_movement': 'camera_providers',
            }

            field_name = provider_field_map.get(self.stage_type)
            if field_name:
                providers = list(getattr(config, field_name).all())

                if providers:
                    # 简化版: 使用第一个提供商
                    # TODO: 实现负载均衡策略
                    provider = providers[0]

        # 如果没有配置,尝试从提示词模板获取默认模型
        if not provider:
            template = self._get_prompt_template(project)
            # template.model_provider已经通过select_related预加载,可以直接访问
            if template and template.model_provider:
                provider = template.model_provider

        # 最后尝试获取系统默认提供商
        if not provider:
            provider = self._get_default_provider()

        # 使用工厂函数动态创建客户端
        return create_ai_client(provider)

    def _get_default_provider(self) -> ModelProvider:
        """获取默认的LLM提供商"""
        provider = ModelProvider.objects.filter(
            provider_type='llm',
            is_active=True
        ).first()

        if not provider:
            raise Exception("未找到可用的LLM模型提供商,请在后台配置")

        return provider

    def _save_result(
        self,
        project: Project,
        stage: ProjectStage,
        generated_text: str,
        prompt_used: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        保存生成结果到对应的领域模型
        不同阶段保存到不同的模型表
        """
        from apps.content.models import ContentRewrite, Storyboard, CameraMovement

        if self.stage_type == 'rewrite':
            # 保存到 ContentRewrite 模型
            provider = self._get_current_provider(project)

            ContentRewrite.objects.update_or_create(
                project=project,
                defaults={
                    'original_text': project.original_topic,
                    'rewritten_text': generated_text,
                    'prompt_used': prompt_used,
                    'model_provider': provider,
                    'generation_metadata': metadata
                }
            )

        elif self.stage_type == 'storyboard':
            # 分镜生成: 解析JSON并保存到 Storyboard 模型
            storyboard_data = parse_storyboard_json(generated_text)
            scenes = storyboard_data.get('scenes', [])

            provider = self._get_current_provider(project)

            # 批量创建或更新分镜
            for scene in scenes:
                Storyboard.objects.update_or_create(
                    project=project,
                    sequence_number=scene['scene_number'],
                    defaults={
                        'scene_description': scene.get('shot_type', ''),
                        'narration_text': scene.get('narration', ''),
                        'image_prompt': scene.get('visual_prompt', ''),
                        'duration_seconds': scene.get('duration', 3.0),
                        'model_provider': provider,
                        'prompt_used': prompt_used,
                        'generation_metadata': {
                            'shot_type': scene.get('shot_type', ''),
                            'raw_scene_data': scene
                        }
                    }
                )

        elif self.stage_type == 'camera_movement':
            # 运镜生成: 保存到 CameraMovement 模型
            scene_number = metadata.get("index")

            # 获取对应的分镜
            storyboard = Storyboard.objects.filter(
                project=project,
                sequence_number=scene_number
            ).first()

            if not storyboard:
                logger.error(f"未找到序号为 {scene_number} 的分镜")
                return

            provider = self._get_current_provider(project)

            # 解析运镜文本(假设返回的是JSON格式)
            try:
                from apps.projects.utils import parse_json
                camera_data = parse_json(generated_text)

                if not camera_data or not isinstance(camera_data, dict):
                    raise ValueError("解析结果为空或格式错误")

                movement_type = camera_data.get('movement_type', '')
                movement_params = camera_data.get('params', {})

            except (ValueError, KeyError, TypeError) as e:
                # 记录解析失败的原因
                logger.warning(
                    f"运镜数据解析失败: {str(e)}, "
                    f"将原始文本存储到 movement_params"
                )
                movement_type = ''
                movement_params = {'raw_text': generated_text}

            # 保存运镜数据
            CameraMovement.objects.update_or_create(
                storyboard=storyboard,
                defaults={
                    'movement_type': movement_type,
                    'movement_params': movement_params,
                    'model_provider': provider,
                    'prompt_used': prompt_used,
                    'generation_metadata': metadata
                }
            )

    def _get_current_provider(self, project: Project) -> Optional[ModelProvider]:
        """
        获取当前阶段使用的模型提供商

        优先级:
        1. 项目模型配置
        2. 提示词模板配置
        3. 系统默认提供商
        """
        # 1. 从项目模型配置获取
        config = getattr(project, 'model_config', None)

        if config:
            provider_field_map = {
                'rewrite': 'rewrite_providers',
                'storyboard': 'storyboard_providers',
                'camera_movement': 'camera_providers',
            }

            field_name = provider_field_map.get(self.stage_type)
            if field_name:
                providers = list(getattr(config, field_name).all())
                if providers:
                    return providers[0]

        # 2. 从提示词模板获取
        template = self._get_prompt_template(project)
        if template and template.model_provider:
            return template.model_provider

        # 3. 获取系统默认提供商
        return self._get_default_provider()
    
    def _get_max_tokens(self) -> int:
        """获取最大token数(根据阶段类型)"""
        token_map = {
            'rewrite': 2000,
            'storyboard': 4000,
            'camera_movement': 1000,
        }
        return token_map.get(self.stage_type, 2000)

    def _get_temperature(self) -> float:
        """获取temperature参数(根据阶段类型)"""
        temp_map = {
            'rewrite': 0.7,
            'storyboard': 0.8,
            'camera_movement': 0.6,
        }
        return temp_map.get(self.stage_type, 0.7)

    def _get_stage_display_name(self) -> str:
        """获取阶段显示名称"""
        name_map = {
            'rewrite': '改写文案',
            'storyboard': '分镜脚本',
            'camera_movement': '运镜参数',
        }
        return name_map.get(self.stage_type, self.stage_type)
