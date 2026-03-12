"""
提示词调试服务
职责: 执行模板调试、沉淀调试资产、保存模板版本
"""

import asyncio
import inspect
import time
from typing import Any, Dict, Generator, Optional

from django.db import transaction
from django.utils import timezone
from jinja2 import Template, TemplateError

from apps.models.models import ModelProvider
from apps.projects.utils import parse_json, parse_storyboard_json
from core.ai_client.factory import create_ai_client

from .models import (
    GlobalVariable,
    PromptDebugArtifact,
    PromptDebugRun,
    PromptDebugSession,
    PromptTemplate,
)


class PromptDebugService:
    """提示词调试核心服务"""

    STAGE_PROVIDER_TYPE_MAP = {
        'rewrite': 'llm',
        'storyboard': 'llm',
        'camera_movement': 'llm',
        'image_generation': 'text2image',
        'video_generation': 'image2video',
    }

    @classmethod
    def get_or_create_session(cls, template: PromptTemplate, user) -> PromptDebugSession:
        session = PromptDebugSession.objects.filter(
            prompt_template=template,
            created_by=user,
        ).order_by('-updated_at').first()

        if session:
            update_fields = ['updated_at']
            if not session.draft_template_content:
                session.draft_template_content = template.template_content
                update_fields.append('draft_template_content')
            if not session.draft_variables:
                session.draft_variables = template.variables
                update_fields.append('draft_variables')
            if not session.model_provider and template.model_provider:
                session.model_provider = template.model_provider
                update_fields.append('model_provider')
            session.save(update_fields=update_fields)
            return session

        return PromptDebugSession.objects.create(
            prompt_template=template,
            template_set=template.template_set,
            name=f'{template.get_stage_type_display()} 调试',
            stage_type=template.stage_type,
            draft_template_content=template.template_content,
            draft_variables=template.variables,
            model_provider=template.model_provider,
            created_by=user,
        )

    @classmethod
    def get_default_provider(cls, stage_type: str) -> Optional[ModelProvider]:
        provider_type = cls.STAGE_PROVIDER_TYPE_MAP.get(stage_type)
        if not provider_type:
            return None

        return ModelProvider.objects.filter(
            provider_type=provider_type,
            is_active=True,
        ).order_by('-priority', '-created_at').first()

    @classmethod
    def resolve_provider(cls, session: PromptDebugSession, provider_id: Optional[str]) -> Optional[ModelProvider]:
        provider = None
        if provider_id:
            provider = ModelProvider.objects.filter(id=provider_id, is_active=True).first()
        if not provider and session.model_provider and session.model_provider.is_active:
            provider = session.model_provider
        if not provider and session.prompt_template.model_provider and session.prompt_template.model_provider.is_active:
            provider = session.prompt_template.model_provider
        if not provider:
            provider = cls.get_default_provider(session.stage_type)
        return provider

    @classmethod
    def build_template_context(
        cls,
        user,
        variable_values: Optional[Dict[str, Any]] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        source_artifact: Optional[PromptDebugArtifact] = None,
    ) -> Dict[str, Any]:
        global_variables = GlobalVariable.get_variables_for_user(user)
        context = {
            **global_variables,
            **(variable_values or {}),
            **(input_payload or {}),
        }

        if source_artifact:
            context['source_artifact'] = source_artifact.content
            content = source_artifact.content or {}
            if isinstance(content, dict):
                context.update(content)

        return context

    @classmethod
    def render_prompt(cls, template_content: str, context: Dict[str, Any]) -> str:
        jinja_template = Template(template_content)
        return jinja_template.render(**context)

    @classmethod
    def parse_output(cls, stage_type: str, raw_text: str) -> Any:
        if stage_type == 'storyboard':
            return parse_storyboard_json(raw_text)
        if stage_type == 'camera_movement':
            return parse_json(raw_text)
        if stage_type == 'rewrite':
            return {'text': raw_text}
        return {'text': raw_text}

    @classmethod
    def _run_llm(cls, provider: ModelProvider, rendered_prompt: str) -> Dict[str, Any]:
        start_time = time.time()
        client = create_ai_client(provider)
        response = client._generate_text(
            prompt=rendered_prompt,
            max_tokens=provider.max_tokens,
            temperature=provider.temperature,
            top_p=provider.top_p,
        )
        if inspect.isawaitable(response):
            response = asyncio.run(response)
        latency_ms = int((time.time() - start_time) * 1000)
        if not response.success:
            raise ValueError(response.error or 'LLM 调试执行失败')
        return {
            'raw_text': response.text,
            'raw_response': {
                'text': response.text,
                'metadata': response.metadata,
            },
            'latency_ms': response.metadata.get('latency_ms', latency_ms),
        }

    @classmethod
    def _run_text2image(
        cls,
        provider: ModelProvider,
        rendered_prompt: str,
        input_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        start_time = time.time()
        client = create_ai_client(provider)
        extra_config = provider.extra_config or {}
        response = client.generate(
            prompt=rendered_prompt,
            negative_prompt=input_payload.get('negative_prompt', extra_config.get('negative_prompt', '')),
            width=input_payload.get('width', extra_config.get('width', 1024)),
            height=input_payload.get('height', extra_config.get('height', 1024)),
            steps=input_payload.get('steps', extra_config.get('steps', 20)),
            ratio=input_payload.get('ratio', extra_config.get('ratio', '1:1')),
            resolution=input_payload.get('resolution', extra_config.get('resolution', '2k')),
            sample_count=input_payload.get('sample_count', extra_config.get('sample_count', 1)),
        )
        latency_ms = int((time.time() - start_time) * 1000)
        if not response.success:
            raise ValueError(response.error or '文生图调试执行失败')
        return {
            'raw_text': '',
            'raw_response': {
                'data': response.data,
                'metadata': response.metadata,
            },
            'latency_ms': response.metadata.get('latency_ms', latency_ms),
            'parsed_output': {
                'images': response.data,
            },
        }

    @classmethod
    def _run_image2video(
        cls,
        provider: ModelProvider,
        rendered_prompt: str,
        input_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        start_time = time.time()
        client = create_ai_client(provider)
        image_url = input_payload.get('image_url') or input_payload.get('url')
        if not image_url:
            raise ValueError('图生视频调试缺少 image_url')

        camera_movement = input_payload.get('camera_movement', {})
        response = None
        if hasattr(client, '_generate_video'):
            response = client._generate_video(
                image_url=image_url,
                camera_movement=camera_movement,
                duration=input_payload.get('duration', 5),
                fps=input_payload.get('fps', 24),
                prompt=rendered_prompt,
            )
            if inspect.isawaitable(response):
                response = asyncio.run(response)
        else:
            response = client.generate(
                image_url=image_url,
                camera_movement=camera_movement,
                duration=input_payload.get('duration', 5),
                fps=input_payload.get('fps', 24),
                prompt=rendered_prompt,
            )
            if inspect.isawaitable(response):
                response = asyncio.run(response)

        latency_ms = int((time.time() - start_time) * 1000)
        if not response.success:
            raise ValueError(response.error or '图生视频调试执行失败')
        return {
            'raw_text': '',
            'raw_response': {
                'data': response.data,
                'metadata': response.metadata,
            },
            'latency_ms': response.metadata.get('latency_ms', latency_ms),
            'parsed_output': {
                'videos': response.data,
            },
        }

    @classmethod
    def create_artifacts(
        cls,
        run: PromptDebugRun,
        parsed_output: Any,
        source_artifact: Optional[PromptDebugArtifact] = None,
    ) -> None:
        PromptDebugArtifact.objects.filter(run=run).delete()

        if run.stage_type == 'storyboard' and isinstance(parsed_output, dict):
            scenes = parsed_output.get('scenes', [])
            bundle = PromptDebugArtifact.objects.create(
                run=run,
                source_artifact=source_artifact,
                artifact_type='storyboard_bundle',
                stage_type=run.stage_type,
                name='分镜输出集合',
                content=parsed_output,
                preview_text=f'共 {len(scenes)} 条分镜',
                created_by=run.session.created_by,
            )
            for scene in scenes:
                PromptDebugArtifact.objects.create(
                    run=run,
                    source_artifact=bundle,
                    artifact_type='storyboard_item',
                    stage_type=run.stage_type,
                    name=f"分镜 {scene.get('scene_number', '')}",
                    sequence_number=scene.get('scene_number'),
                    content=scene,
                    preview_text=scene.get('narration', '')[:200],
                    created_by=run.session.created_by,
                )
            return

        if run.stage_type == 'image_generation':
            images = parsed_output.get('images', []) if isinstance(parsed_output, dict) else []
            for index, image in enumerate(images, 1):
                PromptDebugArtifact.objects.create(
                    run=run,
                    source_artifact=source_artifact,
                    artifact_type='image',
                    stage_type=run.stage_type,
                    name=f'调试图片 {index}',
                    sequence_number=index,
                    content=image,
                    preview_image_url=image.get('url', ''),
                    preview_text=run.rendered_prompt[:200],
                    created_by=run.session.created_by,
                )
            return

        if run.stage_type == 'video_generation':
            videos = parsed_output.get('videos', []) if isinstance(parsed_output, dict) else []
            for index, video in enumerate(videos, 1):
                PromptDebugArtifact.objects.create(
                    run=run,
                    source_artifact=source_artifact,
                    artifact_type='video',
                    stage_type=run.stage_type,
                    name=f'调试视频 {index}',
                    sequence_number=index,
                    content=video,
                    preview_video_url=video.get('url', ''),
                    preview_text=run.rendered_prompt[:200],
                    created_by=run.session.created_by,
                )
            return

        PromptDebugArtifact.objects.create(
            run=run,
            source_artifact=source_artifact,
            artifact_type='text',
            stage_type=run.stage_type,
            name='文本输出',
            content=parsed_output if isinstance(parsed_output, dict) else {'text': parsed_output},
            preview_text=str(parsed_output)[:500],
            created_by=run.session.created_by,
        )

    @classmethod
    def prepare_run_context(
        cls,
        session: PromptDebugSession,
        user,
        template_content: str,
        variable_values: Optional[Dict[str, Any]],
        input_payload: Optional[Dict[str, Any]],
        source_artifact_id: Optional[str],
        provider_id: Optional[str],
    ) -> Dict[str, Any]:
        source_artifact = None
        if source_artifact_id:
            source_artifact = PromptDebugArtifact.objects.filter(
                id=source_artifact_id,
                created_by=user,
            ).first()

        provider = cls.resolve_provider(session, provider_id)
        if not provider:
            raise ValueError('当前阶段没有可用模型，请先配置模型')

        expected_provider_type = cls.STAGE_PROVIDER_TYPE_MAP.get(session.stage_type)
        if expected_provider_type and provider.provider_type != expected_provider_type:
            raise ValueError('选择的模型类型与当前阶段不匹配')

        context = cls.build_template_context(
            user=user,
            variable_values=variable_values,
            input_payload=input_payload,
            source_artifact=source_artifact,
        )

        try:
            rendered_prompt = cls.render_prompt(template_content, context)
        except TemplateError as exc:
            raise ValueError(f'模板渲染失败: {exc}')

        return {
            'provider': provider,
            'source_artifact': source_artifact,
            'resolved_variables': context,
            'rendered_prompt': rendered_prompt,
        }

    @classmethod
    def create_run_record(
        cls,
        session: PromptDebugSession,
        provider: ModelProvider,
        source_artifact: Optional[PromptDebugArtifact],
        template_content: str,
        variable_values: Optional[Dict[str, Any]],
        input_payload: Optional[Dict[str, Any]],
        resolved_variables: Dict[str, Any],
        rendered_prompt: str,
    ) -> PromptDebugRun:
        return PromptDebugRun.objects.create(
            session=session,
            stage_type=session.stage_type,
            status='running',
            source_artifact=source_artifact,
            model_provider=provider,
            template_snapshot=template_content,
            variable_values=variable_values or {},
            input_payload=input_payload or {},
            resolved_variables=resolved_variables,
            rendered_prompt=rendered_prompt,
        )

    @classmethod
    def finalize_run(
        cls,
        session: PromptDebugSession,
        run: PromptDebugRun,
        template_content: str,
        variable_values: Optional[Dict[str, Any]],
        input_payload: Optional[Dict[str, Any]],
        provider: ModelProvider,
        source_artifact: Optional[PromptDebugArtifact],
        raw_response: Dict[str, Any],
        parsed_output: Any,
        latency_ms: int,
    ) -> PromptDebugRun:
        run.raw_response = raw_response
        run.parsed_output = parsed_output
        run.latency_ms = latency_ms
        run.status = 'completed'
        run.error_message = ''
        run.save(update_fields=[
            'raw_response', 'parsed_output', 'latency_ms', 'status', 'error_message', 'updated_at'
        ])

        cls.create_artifacts(run, parsed_output, source_artifact=source_artifact)

        session.draft_template_content = template_content
        session.draft_variables = session.draft_variables or session.prompt_template.variables
        session.model_provider = provider
        session.latest_variable_values = variable_values or {}
        session.latest_input_payload = input_payload or {}
        session.latest_source_artifact = source_artifact
        session.last_run_at = timezone.now()
        session.save(update_fields=[
            'draft_template_content', 'draft_variables', 'model_provider',
            'latest_variable_values', 'latest_input_payload', 'latest_source_artifact',
            'last_run_at', 'updated_at'
        ])
        return run

    @classmethod
    def fail_run(cls, run: Optional[PromptDebugRun], message: str) -> None:
        if not run:
            return
        run.status = 'failed'
        run.error_message = message
        run.save(update_fields=['status', 'error_message', 'updated_at'])

    @classmethod
    def stream_llm_session(
        cls,
        session: PromptDebugSession,
        user,
        template_content: str,
        variable_values: Optional[Dict[str, Any]],
        input_payload: Optional[Dict[str, Any]],
        source_artifact_id: Optional[str],
        provider_id: Optional[str],
    ) -> Generator[Dict[str, Any], None, None]:
        prepared = cls.prepare_run_context(
            session=session,
            user=user,
            template_content=template_content,
            variable_values=variable_values,
            input_payload=input_payload,
            source_artifact_id=source_artifact_id,
            provider_id=provider_id,
        )
        provider = prepared['provider']
        source_artifact = prepared['source_artifact']
        resolved_variables = prepared['resolved_variables']
        rendered_prompt = prepared['rendered_prompt']
        run = cls.create_run_record(
            session=session,
            provider=provider,
            source_artifact=source_artifact,
            template_content=template_content,
            variable_values=variable_values,
            input_payload=input_payload,
            resolved_variables=resolved_variables,
            rendered_prompt=rendered_prompt,
        )

        yield {
            'type': 'run_started',
            'run_id': str(run.id),
            'rendered_prompt': rendered_prompt,
            'resolved_variables': resolved_variables,
        }

        client = create_ai_client(provider)
        if not hasattr(client, 'generate_stream'):
            result = cls._run_llm(provider, rendered_prompt)
            parsed_output = cls.parse_output(session.stage_type, result['raw_text'])
            cls.finalize_run(
                session=session,
                run=run,
                template_content=template_content,
                variable_values=variable_values,
                input_payload=input_payload,
                provider=provider,
                source_artifact=source_artifact,
                raw_response=result['raw_response'],
                parsed_output=parsed_output,
                latency_ms=result['latency_ms'],
            )
            yield {
                'type': 'done',
                'run_id': str(run.id),
                'full_text': result['raw_text'],
                'parsed_output': parsed_output,
                'latency_ms': result['latency_ms'],
            }
            return

        full_text = ''
        start_time = time.time()
        try:
            stream = client.generate_stream(
                prompt='请基于以上指令完成输出',
                system_prompt=rendered_prompt,
                max_tokens=provider.max_tokens,
                temperature=provider.temperature,
                top_p=provider.top_p,
            )
            for chunk in stream:
                chunk_type = chunk.get('type')
                if chunk_type == 'token':
                    full_text = chunk.get('full_text', full_text + chunk.get('content', ''))
                    yield {
                        'type': 'token',
                        'run_id': str(run.id),
                        'content': chunk.get('content', ''),
                        'full_text': full_text,
                    }
                elif chunk_type == 'done':
                    full_text = chunk.get('full_text', full_text)
                    latency_ms = chunk.get('metadata', {}).get('latency_ms') or int((time.time() - start_time) * 1000)
                    parsed_output = cls.parse_output(session.stage_type, full_text)
                    raw_response = {
                        'text': full_text,
                        'metadata': chunk.get('metadata', {}),
                    }
                    cls.finalize_run(
                        session=session,
                        run=run,
                        template_content=template_content,
                        variable_values=variable_values,
                        input_payload=input_payload,
                        provider=provider,
                        source_artifact=source_artifact,
                        raw_response=raw_response,
                        parsed_output=parsed_output,
                        latency_ms=latency_ms,
                    )
                    yield {
                        'type': 'done',
                        'run_id': str(run.id),
                        'full_text': full_text,
                        'parsed_output': parsed_output,
                        'latency_ms': latency_ms,
                    }
                    return
                elif chunk_type == 'error':
                    message = chunk.get('error') or '流式调试失败'
                    cls.fail_run(run, message)
                    yield {
                        'type': 'error',
                        'run_id': str(run.id),
                        'error': message,
                    }
                    return
        except Exception as exc:
            cls.fail_run(run, str(exc))
            yield {
                'type': 'error',
                'run_id': str(run.id),
                'error': str(exc),
            }

    @classmethod
    @transaction.atomic
    def run_session(
        cls,
        session: PromptDebugSession,
        user,
        template_content: str,
        variable_values: Optional[Dict[str, Any]],
        input_payload: Optional[Dict[str, Any]],
        source_artifact_id: Optional[str],
        provider_id: Optional[str],
    ) -> PromptDebugRun:
        prepared = cls.prepare_run_context(
            session=session,
            user=user,
            template_content=template_content,
            variable_values=variable_values,
            input_payload=input_payload,
            source_artifact_id=source_artifact_id,
            provider_id=provider_id,
        )
        source_artifact = prepared['source_artifact']
        provider = prepared['provider']
        context = prepared['resolved_variables']
        rendered_prompt = prepared['rendered_prompt']

        run = cls.create_run_record(
            session=session,
            provider=provider,
            source_artifact=source_artifact,
            template_content=template_content,
            variable_values=variable_values,
            input_payload=input_payload,
            resolved_variables=context,
            rendered_prompt=rendered_prompt,
        )

        if session.stage_type in ('rewrite', 'storyboard', 'camera_movement'):
            result = cls._run_llm(provider, rendered_prompt)
            parsed_output = cls.parse_output(session.stage_type, result['raw_text'])
        elif session.stage_type == 'image_generation':
            result = cls._run_text2image(provider, rendered_prompt, input_payload or {})
            parsed_output = result['parsed_output']
        elif session.stage_type == 'video_generation':
            result = cls._run_image2video(provider, rendered_prompt, input_payload or {})
            parsed_output = result['parsed_output']
        else:
            raise ValueError('暂不支持的调试阶段')

        cls.finalize_run(
            session=session,
            run=run,
            template_content=template_content,
            variable_values=variable_values,
            input_payload=input_payload,
            provider=provider,
            source_artifact=source_artifact,
            raw_response=result['raw_response'],
            parsed_output=parsed_output,
            latency_ms=result['latency_ms'],
        )
        return run

    @classmethod
    @transaction.atomic
    def save_to_template(
        cls,
        session: PromptDebugSession,
        template_content: str,
        variables: Dict[str, Any],
        model_provider_id: Optional[str],
    ) -> PromptTemplate:
        provider = None
        if model_provider_id:
            provider = ModelProvider.objects.filter(id=model_provider_id).first()

        template = session.prompt_template
        template.template_content = template_content
        template.variables = variables
        template.model_provider = provider or session.model_provider
        template.save()

        session.draft_template_content = template_content
        session.draft_variables = variables
        session.model_provider = template.model_provider
        session.save(update_fields=['draft_template_content', 'draft_variables', 'model_provider', 'updated_at'])

        return template

    @classmethod
    @transaction.atomic
    def create_template_version(
        cls,
        session: PromptDebugSession,
        template_content: str,
        variables: Dict[str, Any],
        model_provider_id: Optional[str],
    ) -> PromptTemplate:
        provider = None
        if model_provider_id:
            provider = ModelProvider.objects.filter(id=model_provider_id).first()

        current_template = session.prompt_template
        new_template = PromptTemplate.objects.create(
            template_set=current_template.template_set,
            stage_type=current_template.stage_type,
            template_content=template_content,
            variables=variables,
            version=current_template.version + 1,
            is_active=True,
            model_provider=provider or session.model_provider or current_template.model_provider,
        )

        current_template.is_active = False
        current_template.save(update_fields=['is_active', 'updated_at'])

        session.prompt_template = new_template
        session.template_set = new_template.template_set
        session.stage_type = new_template.stage_type
        session.draft_template_content = template_content
        session.draft_variables = variables
        session.model_provider = new_template.model_provider
        session.save(update_fields=[
            'prompt_template', 'template_set', 'stage_type', 'draft_template_content',
            'draft_variables', 'model_provider', 'updated_at'
        ])

        return new_template
