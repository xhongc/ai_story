"""优云智算 MiniMax H3 视频任务接口。"""

import time
from urllib.parse import urlparse

import requests

from core.ai_client.metaso_h3_client import MetasoH3Client


class UCloudH3Client(MetasoH3Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_token.startswith('sk-ml-'):
            raise ValueError('优云智算视频 API Key 须以 sk-ml- 开头')

    def _build_image_inputs_for_openai_videos(self, image_uris, resolved_image_base64s, image_mime_type):
        images = []
        for item in image_uris or []:
            url = item.get('url') if isinstance(item, dict) else item
            if isinstance(url, str) and url.startswith('/api/v1/content/storage/image/'):
                encoded = self._read_storage_image_as_base64(url)
                images.append(f'data:{image_mime_type};base64,{encoded}')
            elif isinstance(url, str) and url.startswith(('http://', 'https://', 'data:')):
                images.append(url)
        for encoded in resolved_image_base64s or []:
            images.append(f'data:{image_mime_type};base64,{encoded}')
        return list(dict.fromkeys(images))

    def create_video_task(self, prompt, model='MiniMax-H3', duration_seconds=5,
                          aspect_ratio='16:9', resolution=None, image_uri=None,
                          image_uris=None, image_base64=None, image_base64s=None,
                          image_mime_type='image/jpeg', negative_prompt=None,
                          generate_audio=True, camera_movement_description=None,
                          content=None, **kwargs):
        if model not in {'MiniMax-H3', 'minimax-h3-lite'}:
            raise ValueError('优云智算 H3 模型名称无效')
        if type(duration_seconds) is not int or not 4 <= duration_seconds <= 30:
            raise ValueError('优云智算 H3 时长须为 4～30 秒的整数')
        quality = (resolution or '768P').upper()
        if quality not in {'480P', '768P', '1080P', '2K', '4K'}:
            raise ValueError('优云智算 H3 分辨率无效')
        if aspect_ratio not in {'adaptive', '21:9', '16:9', '4:3', '1:1', '3:4', '9:16'}:
            raise ValueError('优云智算 H3 宽高比无效')

        if content is None:
            images = list(image_uris or [])
            if image_uri and image_uri not in images:
                images.insert(0, image_uri)
            encoded_images = list(image_base64s or [])
            if image_base64 and image_base64 not in encoded_images:
                encoded_images.insert(0, image_base64)
            image_inputs = self._build_image_inputs_for_openai_videos(images, encoded_images, image_mime_type)
            if len(image_inputs) > 2:
                raise ValueError('优云智算 H3 最多接受一张首帧和一张尾帧图片')
            text = self._build_prompt_text(prompt, negative_prompt, camera_movement_description)
            content = ([{'type': 'text', 'text': text}] if text else []) + [
                {'type': 'image_url', 'image_url': {'url': url},
                 'role': 'first_frame' if index == 0 else 'last_frame'}
                for index, url in enumerate(image_inputs)
            ]
        if not isinstance(content, list) or not content or not all(isinstance(item, dict) for item in content):
            raise ValueError('优云智算 H3 content 须为非空对象数组')
        counts = {'first_frame': 0, 'last_frame': 0, 'reference_image': 0,
                  'reference_video': 0, 'reference_audio': 0}
        text_length = 0
        for item in content:
            kind = item.get('type')
            if kind == 'text':
                value = item.get('text')
                if not isinstance(value, str):
                    raise ValueError('优云智算 H3 文本素材缺少 text')
                text_length += len(value)
                continue
            field = {'image_url': 'image_url', 'video_url': 'video_url',
                     'audio_url': 'audio_url'}.get(kind)
            url = item.get(field, {}).get('url') if field and isinstance(item.get(field), dict) else None
            if not isinstance(url, str) or not url.startswith(('http://', 'https://', 'data:')):
                raise ValueError('优云智算 H3 素材类型或 URL 无效')
            role = item.get('role') or ('first_frame' if kind == 'image_url' else None)
            allowed = {'image_url': {'first_frame', 'last_frame', 'reference_image'},
                       'video_url': {'reference_video'},
                       'audio_url': {'reference_audio'}}[kind]
            if role not in allowed:
                raise ValueError('优云智算 H3 素材 role 无效')
            counts[role] += 1
        if text_length > 10000 or (not text_length and not any(counts.values())):
            raise ValueError('优云智算 H3 提示词须在 10000 字以内，且需提供文本或素材')
        if (counts['first_frame'] > 1 or counts['last_frame'] > 1 or
                counts['reference_image'] > 9 or counts['reference_video'] > 3 or
                counts['reference_audio'] > 3 or
                sum(counts[role] for role in ('reference_image', 'reference_video', 'reference_audio')) > 12 or
                ((counts['first_frame'] or counts['last_frame']) and
                 (counts['reference_image'] or counts['reference_video'] or counts['reference_audio']))):
            raise ValueError('优云智算 H3 素材数量或组合无效')

        payload = {
            'model': model, 'content': content, 'resolution': quality,
            'duration': duration_seconds, 'ratio': aspect_ratio,
        }
        for key in ('callback_url', 'callback_token', 'use_context_ir', 'skill_id',
                    'aigc_watermark'):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        if not generate_audio:
            payload['mute_audio'] = True
        elif 'mute_audio' in kwargs:
            payload['mute_audio'] = kwargs['mute_audio']
        for key in ('use_context_ir', 'mute_audio', 'aigc_watermark'):
            if key in payload and type(payload[key]) is not bool:
                raise ValueError(f'{key} 须为布尔值')
        if payload.get('callback_token') and not payload.get('callback_url'):
            raise ValueError('callback_token 需要同时提供 callback_url')
        callback_url = payload.get('callback_url')
        if callback_url and (len(callback_url) > 1024 or urlparse(callback_url).scheme not in {'http', 'https'}
                             or not urlparse(callback_url).netloc):
            raise ValueError('callback_url 须为不超过 1024 字符的绝对 HTTP URL')
        if payload.get('callback_token') and len(payload['callback_token']) > 512:
            raise ValueError('callback_token 不能超过 512 字符')
        if payload.get('skill_id') and payload.get('use_context_ir') is not True:
            raise ValueError('skill_id 需要同时设置 use_context_ir=true')

        headers = dict(self.headers)
        if kwargs.get('idempotency_key'):
            if len(kwargs['idempotency_key']) > 128:
                raise ValueError('Idempotency-Key 不能超过 128 字符')
            headers['Idempotency-Key'] = kwargs['idempotency_key']
        response = requests.post(self.base_url, json=payload, headers=headers,
                                 timeout=kwargs.get('timeout', self.timeout))
        response.raise_for_status()
        result = response.json()
        self._check_api_error(result)
        return result

    @staticmethod
    def _check_api_error(result):
        if isinstance(result, dict) and (result.get('type') == 'error' or result.get('RetCode')):
            error = result.get('error') or {}
            message = error.get('message') if isinstance(error, dict) else str(error)
            raise ValueError(message or result.get('Message') or '优云智算 H3 接口错误')

    def get_task_status(self, task_id):
        response = requests.get(self._build_task_status_url(task_id),
                                headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        result = response.json()
        self._check_api_error(result)
        task = result.get('task')
        if not isinstance(task, dict) or not task.get('status'):
            raise ValueError('优云智算 H3 查询响应缺少 task.status')
        return task

    def _extract_video_data_from_task_result(self, task_result, task_id):
        url = (task_result.get('content') or {}).get('url')
        if not url:
            raise ValueError('优云智算 H3 任务已完成，但响应中缺少 content.url')
        video = {'url': url}
        for key in ('resolution', 'duration', 'ratio', 'usage'):
            if key in task_result:
                video[key] = task_result[key]
        return [video]

    def wait_for_completion(self, task_id, poll_interval=5, max_wait_time=600, callback=None):
        start_time = time.monotonic()
        while time.monotonic() - start_time <= max_wait_time:
            task = self.get_task_status(task_id)
            if callback:
                callback(task)
            status = task['status']
            if status == 'succeeded':
                return task
            if status in {'failed', 'blocked', 'cancelled'}:
                error = task.get('error') or {}
                raise RuntimeError(f"任务{status}: {error.get('message') or status}")
            if status not in {'scheduled', 'moderating', 'queued', 'running'}:
                raise ValueError(f'优云智算 H3 未知任务状态: {status}')
            time.sleep(poll_interval)
        raise TimeoutError(f'任务超时: 等待时间超过 {max_wait_time} 秒')
