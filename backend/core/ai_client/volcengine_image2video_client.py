#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""火山引擎图生视频执行器。"""

import logging
import time
from typing import Any, Dict, List

import requests

from core.ai_client.image2video_client import VideoGeneratorClient

logger = logging.getLogger(__name__)

_VOLC_SUCCESS = frozenset({'succeeded', 'success', 'completed'})
_VOLC_FAILED = frozenset({'failed', 'error', 'cancelled', 'canceled'})


class VolcengineImage2VideoClient(VideoGeneratorClient):
    """对接火山方舟 `contents/generations/tasks` 图生视频任务接口。"""

    def _build_create_task_url(self) -> str:
        """构建火山方舟任务创建地址。"""
        if self.base_url.endswith('/contents/generations/tasks'):
            return self.base_url
        return f'{self.base_url.rstrip("/")}/contents/generations/tasks'

    def _build_task_status_url(self, task_id: str) -> str:
        """构建火山方舟任务状态查询地址。"""
        return f'{self._build_create_task_url().rstrip("/")}/{task_id}'

    def _create_volc_task(self, payload: Dict[str, Any], timeout: int) -> str:
        """提交火山方舟视频任务。"""
        response = requests.post(
            self._build_create_task_url(),
            json=payload,
            headers=self.headers,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        task_id = result.get('id') or result.get('task_id')
        if not task_id:
            raise ValueError(f'方舟响应缺少任务 id: {result}')
        return task_id

    def _get_volc_task(self, task_id: str, timeout: int) -> Dict[str, Any]:
        """查询单次火山方舟任务状态。"""
        response = requests.get(
            self._build_task_status_url(task_id),
            headers=self.headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def _wait_volc_task(
        self,
        task_id: str,
        poll_interval: int,
        max_wait_time: int,
        timeout: int,
        max_poll_attempts: int = 120,
        max_consecutive_errors: int = 5,
    ) -> Dict[str, Any]:
        """轮询等待火山方舟任务完成。"""
        start_time = time.time()
        poll_attempts = 0
        consecutive_errors = 0

        while True:
            if time.time() - start_time > max_wait_time:
                raise TimeoutError(f'任务超时: 超过 {max_wait_time} 秒')

            if poll_attempts >= max_poll_attempts:
                raise TimeoutError(f'任务熔断: 轮询次数超过 {max_poll_attempts} 次')

            try:
                task_info = self._get_volc_task(task_id, timeout=timeout)
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    raise RuntimeError(
                        f'任务熔断: 连续查询异常达到 {max_consecutive_errors} 次, 最后错误: {exc}'
                    )
                logger.warning(
                    '火山方舟任务状态查询异常: task_id=%s attempt=%s error=%s',
                    task_id,
                    consecutive_errors,
                    exc,
                )
                time.sleep(poll_interval)
                continue

            poll_attempts += 1
            status = str(task_info.get('status') or '').lower()

            if status in _VOLC_SUCCESS:
                return task_info

            if status in _VOLC_FAILED:
                message = task_info.get('message') or str(task_info.get('error') or '未知错误')
                raise RuntimeError(f'任务失败: {message}')

            time.sleep(poll_interval)

    def _extract_videos_from_volc_result(self, result: Dict[str, Any]) -> List[dict]:
        """从火山方舟任务结果中提取视频地址。"""
        content = result.get('content')
        if isinstance(content, dict):
            video_url = content.get('video_url') or content.get('url')
            if video_url:
                return [{'url': video_url}]

            videos = content.get('videos')
            if isinstance(videos, list):
                extracted = []
                for item in videos:
                    if isinstance(item, dict) and item.get('url'):
                        extracted.append(item)
                    elif item:
                        extracted.append({'url': item})
                if extracted:
                    return extracted

        data = result.get('data')
        if isinstance(data, list):
            return [item if isinstance(item, dict) else {'url': item} for item in data if item]

        return []

    def _build_volc_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """构建火山方舟图生视频请求体。"""
        timeout = int(kwargs.get('timeout', self.timeout))
        image_uri = kwargs.get('image_uri')
        image_base64 = kwargs.get('image_base64')
        image_mime_type = kwargs.get('image_mime_type', 'image/jpeg')
        negative_prompt = kwargs.get('negative_prompt')
        camera_movement_description = kwargs.get('camera_movement_description')

        resolved_image_base64 = self._resolve_image_base64(image_uri, image_base64, timeout)
        final_prompt = self._build_prompt_text(
            prompt=prompt,
            negative_prompt=negative_prompt,
            camera_movement_description=camera_movement_description,
        )

        content: List[Dict[str, Any]] = [{'type': 'text', 'text': final_prompt}]
        if resolved_image_base64:
            content.append(
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:{image_mime_type};base64,{resolved_image_base64}',
                    },
                }
            )

        payload: Dict[str, Any] = {
            'model': kwargs.get('model') or self.model,
            'content': content,
            'ratio': kwargs.get('aspect_ratio', '16:9'),
            'duration': int(kwargs.get('duration_seconds', kwargs.get('duration', 5))),
            'watermark': bool(kwargs.get('watermark', False)),
        }

        if 'generate_audio' in kwargs:
            payload['generate_audio'] = bool(kwargs['generate_audio'])
        if kwargs.get('resolution'):
            payload['resolution'] = kwargs['resolution']
        if kwargs.get('seed') is not None:
            payload['seed'] = kwargs['seed']
        if kwargs.get('camera_fixed') is not None:
            payload['camera_fixed'] = bool(kwargs['camera_fixed'])

        return payload

    def _generate_video(
        self,
        prompt: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """同步生成火山方舟图生视频并拉取到本地存储。"""
        start_time = time.time()
        timeout = int(kwargs.get('timeout', self.timeout))

        try:
            payload = self._build_volc_payload(prompt=prompt, **kwargs)
            task_id = self._create_volc_task(payload, timeout=timeout)
            result = self._wait_volc_task(
                task_id,
                poll_interval=poll_interval,
                max_wait_time=max_wait_time,
                timeout=timeout,
            )
            video_data = self._extract_videos_from_volc_result(result)
            if not video_data:
                return {
                    'success': False,
                    'data': [],
                    'metadata': {
                        'latency_ms': int((time.time() - start_time) * 1000),
                        'model': kwargs.get('model') or self.model,
                        'request_url': self._build_create_task_url(),
                        'task_id': task_id,
                        'error': '响应中未找到可用视频地址',
                    },
                }

            return {
                'success': True,
                'data': self._localize_video_data(video_data, timeout),
                'metadata': {
                    'latency_ms': int((time.time() - start_time) * 1000),
                    'model': kwargs.get('model') or self.model,
                    'request_url': self._build_create_task_url(),
                    'task_id': task_id,
                    'usage': result.get('usage', {}),
                },
            }
        except Exception as exc:
            logger.error('火山方舟图生视频失败: %s', exc, exc_info=True)
            return {
                'success': False,
                'data': [],
                'metadata': {
                    'latency_ms': int((time.time() - start_time) * 1000),
                    'model': kwargs.get('model') or self.model,
                    'request_url': self._build_create_task_url(),
                },
                'error': str(exc),
            }
