#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成API客户端
支持视频生成任务提交和轮询查询
"""

import base64
import re
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from core.utils.file_storage import video_storage
from django.conf import settings


class TaskStatus(Enum):
    """任务状态枚举"""
    INITIALIZING = "Initializing"
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    SUCCESS = "SUCCESS"
    FAILED = "Failed"
    UPLOADING = "Uploading"
    UNKNOWN = "Unknown"


class VideoGeneratorClient:
    """视频生成客户端"""

    VIDEO_TAG_PATTERN = re.compile(
        r'<video[^>]+src=["\'](https?://[^"\']+)["\']',
        re.IGNORECASE,
    )
    URL_PATTERN = re.compile(r'https?://\S+')

    def __init__(
        self,
        api_url: str,
        api_token: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs,
    ):
        """初始化视频生成客户端。"""
        resolved_api_token = api_token or api_key or ''
        resolved_model = model or model_name or ''

        self.api_token = resolved_api_token
        self.base_url = api_url
        self.model = resolved_model
        self.timeout = kwargs.get('timeout', 60)
        self.headers = {
            'Authorization': f'Bearer {resolved_api_token}',
            'Content-Type': 'application/json',
        }

    def _is_chat_completions_endpoint(self, api_url: str) -> bool:
        """判断是否为 chat/completions 接口。"""
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/chat/completions')

    def _is_video_generations_endpoint(self, api_url: str) -> bool:
        """判断是否为 video(s)/generations 接口。"""
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/video/generations') or path.endswith('/videos/generations')

    def _is_openai_videos_endpoint(self, api_url: str) -> bool:
        """判断是否为 OpenAI 风格的 /v1/videos 接口。"""
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/videos') and not path.endswith('/videos/generations')

    def _build_create_video_url(self) -> str:
        """构建视频生成请求地址。"""
        return self.base_url

    def _build_task_status_url(self, task_id: str) -> str:
        """构建任务状态查询地址。"""
        if self._is_chat_completions_endpoint(self.base_url):
            raise ValueError('chat/completions 接口不支持任务轮询')

        create_url = self._build_create_video_url().rstrip('/')
        return f"{create_url}/{task_id}"

    def _build_task_content_url(self, task_id: str) -> str:
        """构建任务内容下载地址。"""
        create_url = self._build_create_video_url().rstrip('/')
        return f"{create_url}/{task_id}/content"

    def _extract_video_urls(self, content: str) -> List[str]:
        """从响应内容中提取视频地址。"""
        if not content:
            return []

        urls = self.VIDEO_TAG_PATTERN.findall(content)
        if urls:
            return list(dict.fromkeys(urls))

        fallback_urls = []
        for candidate in self.URL_PATTERN.findall(content):
            cleaned = candidate.rstrip(').,]"\'\n\r\t >')
            if cleaned:
                fallback_urls.append(cleaned)
        return list(dict.fromkeys(fallback_urls))

    def _build_storage_url(self, relative_path: str) -> str:
        """构建本地视频访问地址。"""
        return f'/api/v1/content/storage/video/{relative_path}'

    def _read_storage_image_as_base64(self, image_url: str) -> str:
        """读取本地 storage/image 下的图片并转换为 base64。"""
        relative_path = image_url.split('/api/v1/content/storage/image/', 1)[1]
        image_root = (Path(settings.STORAGE_ROOT) / 'image').resolve()
        image_path = (image_root / relative_path).resolve()
        if not image_path.is_relative_to(image_root):
            raise ValueError('图片路径超出本地存储目录')
        image_bytes = image_path.read_bytes()
        return base64.b64encode(image_bytes).decode('utf-8')

    def _read_image_url_as_base64(self, image_url: str, timeout: int) -> str:
        """读取图片URL并转换为 base64 字符串。"""
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')

    def _resolve_image_base64(
        self,
        image_uri: Optional[str],
        image_base64: Optional[str],
        timeout: int,
    ) -> str:
        """统一解析图生视频输入图片为 base64。"""
        if image_base64:
            return image_base64

        image_url = image_uri.get('url') if isinstance(image_uri, dict) else image_uri
        if not image_url:
            return ''

        if image_url.startswith('data:') and ';base64,' in image_url:
            return image_url.split(';base64,', 1)[1]
        if image_url.startswith('/api/v1/content/storage/image/'):
            return self._read_storage_image_as_base64(image_url)

        return self._read_image_url_as_base64(image_url, timeout)

    def _resolve_image_base64s(
        self,
        image_uris: Optional[List[Any]],
        image_base64s: Optional[List[str]],
        timeout: int,
    ) -> List[str]:
        """统一解析多张输入图片为 base64 列表。"""
        resolved_images = []

        normalized_base64s = [item for item in (image_base64s or []) if item]
        for item in normalized_base64s:
            resolved_images.append(item)

        for item in image_uris or []:
            resolved = self._resolve_image_base64(item, None, timeout)
            if resolved:
                resolved_images.append(resolved)

        deduplicated = []
        seen = set()
        for item in resolved_images:
            if item in seen:
                continue
            seen.add(item)
            deduplicated.append(item)

        return deduplicated

    def _build_image_inputs_for_openai_videos(
        self,
        image_uris: Optional[List[Any]],
        resolved_image_base64s: Optional[List[str]],
        image_mime_type: str,
    ) -> List[str]:
        """构建 /v1/videos 所需的图片输入列表。"""
        image_inputs = []

        for item in image_uris or []:
            image_url = item.get('url') if isinstance(item, dict) else item
            if not image_url:
                continue
            if isinstance(image_url, str) and (
                image_url.startswith('http://')
                or image_url.startswith('https://')
                or image_url.startswith('data:')
            ):
                image_inputs.append(image_url)

        for image_base64 in resolved_image_base64s or []:
            image_inputs.append(f'data:{image_mime_type};base64,{image_base64}')

        deduplicated = []
        seen = set()
        for item in image_inputs:
            if item in seen:
                continue
            seen.add(item)
            deduplicated.append(item)
        return deduplicated

    def _get_video_extension(self, content_type: str = '', source_url: str = '') -> str:
        """根据响应头或URL推断视频扩展名。"""
        type_map = {
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/webm': '.webm',
            'video/x-msvideo': '.avi',
            'video/x-matroska': '.mkv',
        }
        normalized_type = (content_type or '').split(';', 1)[0].strip().lower()
        if normalized_type in type_map:
            return type_map[normalized_type]

        path = urlparse(source_url).path.lower()
        for extension in ('.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv'):
            if path.endswith(extension):
                return extension

        return '.mp4'

    def _download_video_to_storage(
        self,
        video_url: str,
        timeout: int,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> dict:
        """下载远程视频到本地存储并返回本地访问地址。"""
        if video_url.startswith('/api/v1/content/storage/video/'):
            relative_path = video_url.split('/api/v1/content/storage/video/', 1)[1]
            return {
                'url': video_url,
                'storage_path': relative_path,
                'original_url': video_url,
            }

        response = requests.get(video_url, stream=True, timeout=timeout, headers=request_headers)
        response.raise_for_status()
        extension = self._get_video_extension(
            content_type=response.headers.get('Content-Type', ''),
            source_url=video_url,
        )
        filename = f'video_{uuid.uuid4().hex}{extension}'
        full_path, relative_path = video_storage.get_unique_filepath(
            filename=filename,
            create_dirs=True,
        )

        with open(full_path, 'wb') as output_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    output_file.write(chunk)

        return {
            'url': self._build_storage_url(relative_path),
            'storage_path': relative_path,
            'original_url': video_url,
        }

    def _localize_video_item(self, item: Any, timeout: int) -> dict:
        """将单个视频结果下载到本地。"""
        original_item = item if isinstance(item, dict) else {'url': item}
        video_url = original_item.get('url') or original_item.get('content_url') or ''
        localized = dict(original_item)

        if not video_url:
            return localized

        try:
            localized.update(
                self._download_video_to_storage(
                    video_url,
                    timeout,
                    request_headers=original_item.get('download_headers'),
                )
            )
        except Exception as exc:
            localized['download_error'] = str(exc)
            localized.setdefault('original_url', video_url)
        return localized

    def _localize_video_data(self, video_data: List[dict], timeout: int) -> List[dict]:
        """批量将视频结果下载到本地。"""
        return [self._localize_video_item(item, timeout) for item in video_data]

    def _build_prompt_text(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        camera_movement_description: Optional[str] = None,
    ) -> str:
        """构建最终发送给模型的文本提示词。"""
        parts = [prompt.strip()] if prompt else []

        if camera_movement_description:
            parts.append(f'运镜描述：{camera_movement_description.strip()}')
        if negative_prompt:
            parts.append(f'负面提示词：{negative_prompt.strip()}')

        return '\n\n'.join([item for item in parts if item])

    def _build_openai_videos_payload(
        self,
        model: str,
        prompt: str,
        duration_seconds: int,
        sample_count: int,
        aspect_ratio: str,
        generate_audio: bool,
        resolution: Optional[str],
        seed: Optional[int],
        negative_prompt: Optional[str],
        image_inputs: List[str],
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建 /v1/videos 请求体。"""
        payload: Dict[str, Any] = {
            'model': model,
            'prompt': prompt,
        }

        if aspect_ratio:
            payload['aspect_ratio'] = aspect_ratio
        # 暂时注释，sora 模型不支持
        # if duration_seconds:
        #     payload['duration'] = duration_seconds
        if image_inputs:
            payload['reference_mode'] = 'image'
            payload['image'] = image_inputs

        return payload

    def _extract_task_id(self, task_result: Any) -> str:
        """从创建任务响应中提取任务 ID。"""
        task_id = task_result
        if isinstance(task_result, dict):
            task_id = (
                task_result.get('task_id')
                or task_result.get('id')
                or task_result.get('video_id')
            )
            if not task_id and isinstance(task_result.get('data'), dict):
                data = task_result['data']
                task_id = data.get('task_id') or data.get('id') or data.get('video_id')
        if not task_id:
            raise ValueError('创建视频任务成功，但响应中缺少任务 ID')
        return task_id

    def _normalize_status(self, status_value: Optional[str]) -> str:
        """归一化不同网关的任务状态。"""
        normalized = (status_value or '').strip().lower()
        status_map = {
            'success': TaskStatus.SUCCESS.value,
            'succeeded': TaskStatus.SUCCESS.value,
            'completed': TaskStatus.COMPLETED.value,
            'in_progress': TaskStatus.RUNNING.value,
            'processing': TaskStatus.RUNNING.value,
            'running': TaskStatus.RUNNING.value,
            'queued': TaskStatus.QUEUED.value,
            'pending': TaskStatus.QUEUED.value,
            'failed': TaskStatus.FAILED.value,
            'error': TaskStatus.FAILED.value,
        }
        return status_map.get(normalized, status_value or TaskStatus.UNKNOWN.value)

    def _extract_video_data_from_task_result(self, task_result: Dict[str, Any], task_id: str) -> List[dict]:
        """从任务结果中提取视频列表。"""
        if not isinstance(task_result, dict):
            return []

        direct_video_url = task_result.get('video_url') or task_result.get('url')
        if direct_video_url:
            return [{'url': direct_video_url}]

        data = task_result.get('data')
        if isinstance(data, list):
            videos = []
            for item in data:
                if isinstance(item, dict):
                    video_url = item.get('video_url') or item.get('url')
                    if video_url:
                        videos.append(item if item.get('url') or not item.get('video_url') else {'url': video_url})
                elif item:
                    videos.append({'url': item})
            if videos:
                return videos

        if isinstance(data, dict):
            direct_video_url = data.get('video_url') or data.get('url')
            if direct_video_url:
                return [{'url': direct_video_url}]

            videos = data.get('videos', [])
            if videos:
                return [item if isinstance(item, dict) else {'url': item} for item in videos if item]

            content = data.get('content', {})
            if isinstance(content, dict):
                video_url = content.get('video_url') or content.get('url')
                if video_url:
                    return [{'url': video_url}]

        if self._is_openai_videos_endpoint(self.base_url):
            direct_url = task_result.get('video_url') or task_result.get('url') or task_result.get("metadata", {}).get("url")
            if direct_url:
                return [{'url': direct_url}]
            return [{
                'content_url': self._build_task_content_url(task_id),
                'download_headers': {'Authorization': self.headers['Authorization']},
                'original_url': self._build_task_content_url(task_id),
            }]

        return []

    def create_video_task(
        self,
        prompt: str,
        model: str = 'veo-3.0-fast-generate-preview',
        duration_seconds: int = 8,
        sample_count: int = 1,
        aspect_ratio: str = '16:9',
        generate_audio: bool = True,
        image_uri: Optional[str] = None,
        image_uris: Optional[List[Any]] = None,
        image_base64: Optional[str] = None,
        image_base64s: Optional[List[str]] = None,
        image_mime_type: str = 'image/jpeg',
        resolution: Optional[str] = None,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
        person_generation: str = 'allow_adult',
        camera_movement_description: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建视频生成任务。"""
        url = self._build_create_video_url()
        timeout = kwargs.get('timeout', self.timeout)
        normalized_image_uris = list(image_uris or [])
        if image_uri and image_uri not in normalized_image_uris:
            normalized_image_uris.insert(0, image_uri)

        normalized_image_base64s = list(image_base64s or [])
        if image_base64 and image_base64 not in normalized_image_base64s:
            normalized_image_base64s.insert(0, image_base64)

        final_prompt = self._build_prompt_text(
            prompt=prompt,
            negative_prompt=negative_prompt,
            camera_movement_description=camera_movement_description,
        )

        if self._is_chat_completions_endpoint(url):
            resolved_image_base64s = self._resolve_image_base64s(
                normalized_image_uris,
                normalized_image_base64s,
                timeout,
            )
            message_content = [
                {
                    'type': 'text',
                    'text': final_prompt,
                }
            ]

            for resolved_image_base64 in resolved_image_base64s:
                message_content.append(
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:{image_mime_type};base64,{resolved_image_base64}',
                        },
                    }
                )

            payload = {
                'model': model,
                'messages': [
                    {
                        'role': 'user',
                        'content': message_content,
                    }
                ],
            }

            try:
                response = requests.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                choices = result.get('choices') or []
                if not choices:
                    raise Exception('响应格式错误: 缺少choices字段')

                message = choices[0].get('message') or {}
                content = message.get('content', '')
                video_urls = self._extract_video_urls(content)
                if not video_urls:
                    raise Exception('响应格式错误: 未从message.content中解析到有效视频链接')

                return video_urls
            except requests.exceptions.RequestException as e:
                raise Exception(f'创建视频任务失败: {str(e)}')

        if self._is_openai_videos_endpoint(url):
            image_inputs = self._build_image_inputs_for_openai_videos(
                normalized_image_uris,
                normalized_image_base64s,
                image_mime_type,
            )
            extra_metadata = {}
            if camera_movement_description:
                extra_metadata['camera_movement_description'] = camera_movement_description
            if person_generation:
                extra_metadata['person_generation'] = person_generation

            payload = self._build_openai_videos_payload(
                model=model,
                prompt=final_prompt,
                duration_seconds=duration_seconds,
                sample_count=sample_count,
                aspect_ratio=aspect_ratio,
                generate_audio=generate_audio,
                resolution=resolution,
                seed=seed,
                negative_prompt=negative_prompt,
                image_inputs=image_inputs,
                extra_metadata=extra_metadata or None,
            )

            try:
                response = requests.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                raise Exception(f'创建视频任务失败: {str(e)}')

        resolved_image_base64s = self._resolve_image_base64s(
            normalized_image_uris,
            normalized_image_base64s,
            timeout,
        )
        payload = {
            'width': 720,
            'height': 1280,
            'model': model,
            'prompt': final_prompt,
            'filePaths': [],
        }
        if resolved_image_base64s:
            data_urls = [
                f'data:{image_mime_type};base64,{resolved_image_base64}'
                for resolved_image_base64 in resolved_image_base64s
            ]
            payload['images'] = data_urls
        if camera_movement_description:
            payload['cameraMovementDescription'] = camera_movement_description
        if resolution:
            payload['resolution'] = resolution
        if duration_seconds:
            payload['durationSeconds'] = duration_seconds
        if aspect_ratio:
            payload['aspectRatio'] = aspect_ratio
        if sample_count:
            payload['sampleCount'] = sample_count
        if seed is not None:
            payload['seed'] = seed
        if negative_prompt:
            payload['negativePrompt'] = negative_prompt
        if generate_audio and model != 'veo-2.0-generate-001':
            payload['generateAudio'] = generate_audio
        if person_generation:
            payload['personGeneration'] = person_generation

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            data = result.get('data')
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get('task_id') or data.get('id') or data
            return result.get('task_id') or result.get('id') or data
        except requests.exceptions.RequestException as e:
            raise Exception(f'创建视频任务失败: {str(e)}')

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询视频生成任务状态。"""
        url = self._build_task_status_url(task_id)

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f'查询任务状态失败: {str(e)}')

    def wait_for_completion(
        self,
        task_id: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """轮询等待任务完成。"""
        start_time = time.time()

        while True:
            elapsed_time = time.time() - start_time

            if elapsed_time > max_wait_time:
                raise TimeoutError(f'任务超时: 等待时间超过 {max_wait_time} 秒')

            task_info = self.get_task_status(task_id)
            status = task_info.get('status')
            if status is None and "data" in task_info:
                task_info = task_info["data"]
                status = task_info.get("status")
            status = self._normalize_status(status)
            if callback:
                callback(task_info)
            if status == TaskStatus.SUCCESS.value:
                return task_info
            if status == TaskStatus.COMPLETED.value:
                return task_info
            if status == TaskStatus.FAILED.value:
                message = task_info.get('message', '未知错误')
                raise Exception(f'任务失败: {message}')

            time.sleep(poll_interval)

    def _generate_video(
        self,
        prompt: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """同步生成视频(提交任务并等待完成)。"""
        start_time = time.time()
        timeout = kwargs.get('timeout', self.timeout)
        task_result = self.create_video_task(prompt, **kwargs)

        if isinstance(task_result, list):
            video_data = []
            for item in task_result:
                if isinstance(item, dict):
                    url = item.get('url')
                    if not url:
                        continue
                    video_data.append(item)
                elif item:
                    video_data.append({'url': item})

            localized_video_data = self._localize_video_data(video_data, timeout)
            return {
                'success': True,
                'data': localized_video_data,
                'metadata': {
                    'latency_ms': int((time.time() - start_time) * 1000),
                    'model': kwargs.get('model') or self.model,
                    'request_url': self._build_create_video_url(),
                },
            }

        task_id = self._extract_task_id(task_result)

        result = self.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            max_wait_time=max_wait_time,
            callback=None,
        )

        video_data = self._extract_video_data_from_task_result(result, task_id)

        localized_video_data = self._localize_video_data(video_data, timeout)
        return {
            'success': True,
            'data': localized_video_data,
            'metadata': {
                'latency_ms': int((time.time() - start_time) * 1000),
                'model': kwargs.get('model') or self.model,
                'request_url': self._build_create_video_url(),
                'task_id': task_id,
            },
        }
