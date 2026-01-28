"""
图生视频阶段处理器
职责: 为每个已生成的图片调用VideoGenerator生成视频
遵循单一职责原则(SRP) + 开闭原则(OCP)
"""

import copy
import logging
import os
from typing import Any, Dict, Generator, List, Optional

from django.conf import settings
from core.ai_client.factory import create_ai_client
from core.ai_client.image2video_client import TaskStatus, VideoGenerator
from core.pipeline.base import PipelineContext, StageProcessor, StageResult
from django.utils import timezone
from jinja2 import Template, TemplateError
import base64
from pathlib import Path

from apps.models.models import ModelProvider
from apps.projects.models import Project, ProjectStage

logger = logging.getLogger(__name__)


class Image2VideoStageProcessor(StageProcessor):
    """
    图生视频阶段处理器

    职责:
    - 读取image_generation阶段的图片数据
    - 读取camera_movement阶段的运镜参数
    - 为每个图片调用VideoGenerator生成视频
    - 保存生成的视频到GeneratedVideo模型
    - 支持批量生成和流式进度推送

    特性:
    - 异步轮询任务状态
    - 失败自动重试机制
    - 支持流式进度更新
    - 超时控制和错误处理
    """

    def __init__(self):
        """初始化处理器"""
        super().__init__("video_generation")
        self.stage_type = "video_generation"
        self.max_concurrent = 2  # 最大并发生成数(视频生成较慢,建议并发数小一些)
        self.poll_interval = 10  # 轮询间隔(秒)
        self.max_wait_time = 600  # 最大等待时间(秒)

    def validate(self, context: PipelineContext) -> bool:
        """
        验证是否可以执行图生视频阶段

        检查:
        1. 项目是否存在
        2. image_generation阶段是否已完成
        3. camera_movement阶段是否已完成
        4. 是否有图片数据
        5. 是否配置了图生视频模型
        """
        try:
            project = Project.objects.get(id=context.project_id)

            # 检查image_generation阶段是否完成
            image_stage = ProjectStage.objects.filter(
                project=project, stage_type="image_generation", status="completed"
            ).first()

            if not image_stage:
                logger.error(f"项目 {context.project_id} 的image_generation阶段未完成")
                return False

            # 检查camera_movement阶段是否完成
            camera_stage = ProjectStage.objects.filter(
                project=project, stage_type="camera_movement", status="completed"
            ).first()

            if not camera_stage:
                logger.error(f"项目 {context.project_id} 的camera_movement阶段未完成")
                return False

            # 检查是否有图片数据(从output_data验证)
            if image_stage.output_data:
                scenes = image_stage.output_data.get("human_text", {}).get("scenes", [])
                has_images = any(scene.get("urls") for scene in scenes)

                if not has_images:
                    logger.error(f"项目 {context.project_id} 没有图片数据")
                    return False
            else:
                logger.error(
                    f"项目 {context.project_id} 的image_generation阶段没有输出数据"
                )
                return False

            # 检查是否有可用的图生视频模型
            provider = self._get_image2video_provider(project)
            if not provider:
                logger.error(f"项目 {context.project_id} 未配置图生视频模型")
                return False

            return True

        except Project.DoesNotExist:
            logger.error(f"项目 {context.project_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"验证失败: {str(e)}", exc_info=True)
            return False

    def process(self, context: PipelineContext) -> StageResult:
        """
        非流式执行图生视频生成
        用于Pipeline自动执行
        """
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=context.project_id)
            stage, created = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)

            # 更新阶段状态
            stage.status = "processing"
            stage.started_at = timezone.now()
            stage.save()

            # 获取分镜数据(从ProjectStage.output_data读取)
            storyboards = stage.output_data.get("human_text", {}).get("scenes", [])

            if not storyboards:
                return StageResult(
                    success=False, error="没有找到分镜数据", can_retry=False
                )

            # 获取AI客户端
            provider = self._get_image2video_provider(project)
            video_generator = VideoGenerator(
                api_token=provider.api_key, use_backup=False
            )

            # 批量生成视频
            generated_videos = []
            failed_count = 0

            for index, storyboard in enumerate(storyboards, 1):
                try:
                    # 检查是否有图片URL
                    image_urls = storyboard.get("urls", [])
                    if not image_urls:
                        logger.warning(f"分镜 {index} 没有图片URL，跳过")
                        failed_count += 1
                        continue

                    # 生成视频
                    video_url = self._generate_single_video(
                        storyboard=storyboard,
                        scene_number=index,
                        video_generator=video_generator,
                        provider=provider,
                    )

                    if video_url:
                        generated_videos.append(
                            {"scene_number": index, "video_url": video_url}
                        )
                        # 更新output_data
                        storyboard["video_url"] = video_url
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(f"分镜 {index} 视频生成失败: {str(e)}")
                    failed_count += 1

            # 保存最终结果
            success_count = len(generated_videos)
            total = len(storyboards)

            output_data = {
                "human_text": {"scenes": storyboards},
                "total_storyboards": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "generated_videos": generated_videos,
            }

            stage.output_data = output_data
            stage.status = "completed" if failed_count == 0 else "partially_completed"
            stage.completed_at = timezone.now()
            stage.save()

            # 添加到上下文
            context.add_result(self.stage_type, output_data)

            return StageResult(success=True, data=output_data)

        except Exception as e:
            logger.error(f"{self.stage_type} 阶段处理失败: {str(e)}", exc_info=True)
            return StageResult(success=False, error=str(e), can_retry=True)

    def process_stream(
        self, project_id: str, storyboard_ids: List[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行图生视频生成
        用于SSE实时推送进度

        Args:
            project_id: 项目ID
            storyboard_ids: 指定要生成的分镜ID列表(可选,默认生成所有)

        Yields:
            Dict包含: type (progress/task_created/task_status/video_generated/done/error), content, data
        """
        stage = None
        try:
            # 获取项目和阶段
            project = Project.objects.get(id=project_id)
            stage, created = ProjectStage.objects.get_or_create(project=project, stage_type=self.stage_type)

            # 更新阶段状态
            stage.status = "processing"
            stage.started_at = timezone.now()
            stage.save()

            yield {
                "type": "stage_update",
                "stage": {
                    "id": str(stage.id),
                    "status": "processing",
                    "stage_type": self.stage_type,
                    "started_at": stage.started_at.isoformat(),
                },
            }

            # 从 Storyboard 模型获取分镜列表
            from apps.content.models import Storyboard as StoryboardModel

            storyboards_query = StoryboardModel.objects.filter(project=project).order_by('sequence_number')

            # 如果指定了分镜ID,则只处理这些分镜
            if storyboard_ids:
                storyboards_query = storyboards_query.filter(id__in=storyboard_ids)

            storyboards = list(storyboards_query)

            if not storyboards:
                yield {"type": "error", "error": "没有找到分镜数据"}
                return

            total = len(storyboards)
            yield {"type": "info", "message": f"开始生成视频，共 {total} 个分镜..."}

            # 获取AI客户端配置
            provider = self._get_image2video_provider(project)

            # 批量生成视频
            generated_videos = []
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
                        "type": "progress",
                        "current": index,
                        "total": total,
                        "message": f"正在生成第 {index}/{total} 个视频...",
                        "scene_number": storyboard_obj.sequence_number,
                    }

                    # 检查是否有图片URL
                    # 从 GeneratedImage 模型获取该分镜的图片
                    from apps.content.models import GeneratedImage
                    generated_images = GeneratedImage.objects.filter(
                        storyboard=storyboard_obj,
                        status='completed'
                    ).order_by('-created_at')

                    if not generated_images.exists():
                        failed_count += 1
                        yield {
                            "type": "warning",
                            "message": f"分镜 {storyboard_obj.sequence_number} 没有生成的图片，跳过",
                        }
                        continue

                    # 使用第一张生成的图片
                    first_image = generated_images.first()
                    storyboard_dict['urls'] = [{'url': first_image.image_url}]

                    # 生成视频 (流式推送状态更新)
                    video_urls = None
                    for event in self._generate_single_video_stream(
                        project=project,
                        storyboard=storyboard_dict,
                        scene_number=storyboard_obj.sequence_number,
                        provider=provider,
                    ):
                        # 转发所有事件
                        yield event

                        # 保存最终生成的视频URL
                        if event["type"] == "video_generated":
                            video_urls_obj = event.get("video_urls", {})
                            if getattr(video_urls_obj, 'data', None):
                                video_urls = video_urls_obj.data
                            else:
                                video_urls = video_urls_obj.get("data", [])

                    if video_urls:
                        generated_videos.append(
                            {"scene_number": storyboard_obj.sequence_number, "video_urls": video_urls}
                        )

                        # 保存到 GeneratedVideo 模型
                        from apps.content.models import GeneratedVideo, CameraMovement

                        # 获取运镜参数(如果有)
                        camera_movement = CameraMovement.objects.filter(
                            storyboard=storyboard_obj
                        ).first()

                        for video_data in video_urls:
                            GeneratedVideo.objects.create(
                                storyboard=storyboard_obj,
                                image=first_image,
                                camera_movement=camera_movement,
                                video_url=video_data.get('url', ''),
                                thumbnail_url='',
                                generation_params={
                                    'prompt': storyboard_dict.get('visual_prompt', ''),
                                    'model': provider.model_name if provider else '',
                                    'original_data': video_data
                                },
                                model_provider=provider,
                                status='completed',
                                duration=video_data.get('duration', 0),
                                width=video_data.get('width', 0),
                                height=video_data.get('height', 0),
                                fps=video_data.get('fps', 0),
                                file_size=video_data.get('file_size', 0)
                            )
                    else:
                        failed_count += 1
                        yield {
                            "type": "warning",
                            "message": f"分镜 {storyboard_obj.sequence_number} 视频生成失败",
                        }

                except Exception as e:
                    failed_count += 1
                    logger.error(f"分镜 {storyboard_obj.sequence_number} 生成失败: {str(e)}")
                    yield {
                        "type": "error",
                        "error": f"分镜 {storyboard_obj.sequence_number} 生成失败: {str(e)}",
                        "scene_number": storyboard_obj.sequence_number,
                    }

            # 保存最终结果到阶段
            success_count = len(generated_videos)
            output_data = {
                'total_storyboards': total,
                'success_count': success_count,
                'failed_count': failed_count,
                'generated_videos': generated_videos
            }

            stage.output_data = output_data
            stage.status = 'completed' if failed_count == 0 else 'completed'
            stage.completed_at = timezone.now()
            stage.save()

            yield {
                "type": "done",
                "message": f"视频生成完成: 成功 {success_count}/{total}",
                "stage": {
                    "id": str(stage.id),
                    "status": stage.status,
                },
            }

        except Exception as e:
            logger.error(f"流式图生视频处理失败: {str(e)}", exc_info=True)

            # 更新阶段状态
            if stage:
                try:
                    stage.status = "failed"
                    stage.error_message = str(e)
                    stage.save()
                except Exception:
                    pass

            yield {"type": "error", "error": str(e)}

    def on_failure(self, context: PipelineContext, error: Exception):
        """失败处理"""
        try:
            project = Project.objects.get(id=context.project_id)
            stage = ProjectStage.objects.filter(
                    project=project, stage_type=self.stage_type
                ).first()

            if stage:
                stage.status = "failed"
                stage.error_message = str(error)
                stage.save()

        except Exception as e:
            logger.error(f"更新失败状态失败: {str(e)}")

    # ===== 私有辅助方法 =====

    def _get_image2video_provider(
        self, project: Project
    ) -> Optional[ModelProvider]:
        """获取图生视频模型提供商"""
        # 1. 优先从项目模型配置获取
        config = getattr(project, "model_config", None)

        if config:
            providers = list(config.video_providers.all())

            if providers:
                # 简化版: 使用第一个提供商
                # TODO: 实现负载均衡策略
                return providers[0]

        # 2. 获取系统默认提供商
        provider = ModelProvider.objects.filter(
            provider_type="image2video", is_active=True
        ).first()

        if not provider:
            raise Exception("未找到可用的图生视频模型提供商，请在后台配置")

        return provider

    def _generate_single_video(
        self,
        storyboard: Dict[str, Any],
        scene_number: int,
        video_generator: VideoGenerator,
        provider: ModelProvider,
    ) -> Optional[str]:
        """
        为单个分镜生成视频 (非流式版本)

        Args:
            storyboard: 分镜数据字典
            scene_number: 分镜序号
            video_generator: 视频生成器
            provider: 模型提供商

        Returns:
            视频URL或None(失败时)
        """
        try:
            # 准备生成参数
            prompt = self._build_video_prompt(storyboard)
            image_urls = storyboard.get("urls", [])

            if not image_urls:
                logger.error(f"分镜 {scene_number} 没有图片URL")
                return None

            generation_params = {
                "prompt": prompt,
                "model": provider.model_name,
                "image_uri": image_urls[0],  # 使用第一张图片
                "duration_seconds": int(storyboard.get("duration_seconds", 8)),
                "aspect_ratio": "9:16",  # 默认竖屏
                "generate_audio": True,
            }

            # 调用VideoGenerator创建任务 (同步函数,需要在executor中执行)
            task_result = video_generator.create_video_task(**generation_params)

            logger.info(f"分镜 {scene_number} 视频任务已创建: {task_result}")

            # # 轮询等待任务完成
            # task_result = loop.run_in_executor(
            #     None,
            #     lambda: video_generator.wait_for_completion(
            #         task_id=task_id,
            #         poll_interval=self.poll_interval,
            #         max_wait_time=self.max_wait_time
            #     )
            # )

            # 提取视频URL
            videos = task_result
            if not videos:
                logger.error(f"分镜 {scene_number} 任务完成但没有视频数据")
                return None

            video_data = videos[0]  # 取第一个视频
            video_url = video_data.get("url", "")

            logger.info(f"分镜 {scene_number} 视频生成成功: {video_url}")
            return video_url

        except TimeoutError as e:
            logger.error(f"分镜 {scene_number} 视频生成超时: {str(e)}")
            return None

        except Exception as e:
            logger.error(f"分镜 {scene_number} 视频生成异常: {str(e)}", exc_info=True)
            return None

    def image_to_base64(self, image_path):
        """将本地图片转换为 Base64 字符串（带格式前缀）"""
        image = Path(image_path)
        with open(image, "rb") as f:
            base64_str = base64.b64encode(f.read()).decode("utf-8")
        # 自动识别图片格式（根据文件后缀）
        ext = image.suffix.lstrip(".").lower()
        if ext == "jpg":
            ext = "jpeg"  # 标准 MIME 类型是 image/jpeg
        return f"{base64_str}"

    def _generate_single_video_stream(
        self,
        project: Project,
        storyboard: Dict[str, Any],
        scene_number: int,
        provider: ModelProvider,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        为单个分镜生成视频 (流式版本,推送状态更新)

        Args:
            storyboard: 分镜数据字典
            scene_number: 分镜序号
            video_generator: 视频生成器
            provider: 模型提供商

        Yields:
            Dict包含: type (task_created/task_status/video_generated/error), data
        """
        try:
            # 准备生成参数
            # toto test
            try:
                prompt = self._build_prompt(project, storyboard)
            except Exception:
                prompt = ""
            image_urls = storyboard.get("urls", [])

            if not image_urls:
                yield {
                    "type": "error",
                    "error": f"分镜 {scene_number} 没有图片URL",
                    "scene_number": scene_number,
                }
                return

            model_name = provider.model_name
            api_key = provider.api_key
            api_url = provider.api_url
            # 创建任务
            client = create_ai_client(provider)
            video_urls = client._generate_video(
                api_url=api_url,
                session_id=api_key,
                model=model_name,
                prompt=prompt,
            )


            yield {
                "type": "video_generated",
                "scene_number": scene_number,
                "video_urls": video_urls,
            }

        except Exception as e:
            logger.error(
                f"分镜 {scene_number} 流式视频生成异常: {str(e)}", exc_info=True
            )

            yield {"type": "error", "error": str(e), "scene_number": scene_number}
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
    
    def _build_prompt(self, project: Project, storyboard: dict) -> str:
        """
        构建提示词
        从PromptTemplate获取模板并使用Jinja2渲染
        """
        template = self._get_prompt_template(project)

        if not template:
            raise ValueError(f"未找到 {self.stage_type} 阶段的提示词模板")
        urls = storyboard.get("urls", [])
        if not urls:
            raise ValueError(f"分镜 {storyboard.get('scene_number', '')} 没有图片URL")
        storyboard_copy = copy.deepcopy(storyboard)
        image_url = urls[0].get("url", "")
        image_dir = Path(settings.STORAGE_ROOT) / 'image'
        path_list = image_url.split("/")[-2:]
        image_path = Path(image_dir, *path_list)
        base64_image = self.image_to_base64(image_path)
        storyboard_copy["url"] = base64_image
        try:
            # 准备模板变量
            template_vars = {
                'project': {
                    'name': project.name,
                    'description': project.description,
                    'original_topic': project.original_topic,
                },
                **storyboard_copy  # 合并输入数据作为变量
            }

            # 渲染Jinja2模板
            jinja_template = Template(template.template_content)
            rendered_prompt = jinja_template.render(**template_vars)

            return rendered_prompt

        except TemplateError as e:
            logger.error(f"提示词模板渲染失败: {str(e)}")
            raise ValueError(f"提示词模板渲染失败: {str(e)}")