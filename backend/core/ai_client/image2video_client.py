#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成API客户端
支持视频生成任务提交和轮询查询
"""

import re
import time
from enum import Enum
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import requests


class TaskStatus(Enum):
    """任务状态枚举"""
    INITIALIZING = "Initializing"
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
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

    def __init__(self, api_url: str, api_token: str, model: str):
        """初始化视频生成客户端

        Args:
            api_url: API地址或基础地址
            api_token: API认证令牌
            model: 模型名称
        """
        self.api_token = api_token
        self.base_url = api_url
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def _is_chat_completions_endpoint(self, api_url: str) -> bool:
        """判断是否为 chat/completions 接口。"""
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/chat/completions')

    def _is_video_generations_endpoint(self, api_url: str) -> bool:
        """判断是否为 video(s)/generations 接口。"""
        path = urlparse(api_url).path.rstrip('/')
        return path.endswith('/video/generations') or path.endswith('/videos/generations')

    def _build_create_video_url(self) -> str:
        """构建视频生成请求地址。"""
        if self._is_chat_completions_endpoint(self.base_url):
            return self.base_url
        if self._is_video_generations_endpoint(self.base_url):
            return self.base_url
        return f"{self.base_url.rstrip('/')}/v1/videos/generations"

    def _build_task_status_url(self, task_id: str) -> str:
        """构建任务状态查询地址。"""
        if self._is_chat_completions_endpoint(self.base_url):
            raise ValueError('chat/completions 接口不支持任务轮询')

        create_url = self._build_create_video_url().rstrip('/')
        return f"{create_url}/{task_id}"

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

    def create_video_task(
        self,
        prompt: str,
        model: str = "veo-3.0-fast-generate-preview",
        duration_seconds: int = 8,
        sample_count: int = 1,
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
        image_uri: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/jpeg",
        resolution: Optional[str] = None,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
        person_generation: str = "allow_adult"
    ) -> Any:
        """创建视频生成任务

        Args:
            prompt: 视频生成提示词
            model: 模型名称
            duration_seconds: 视频时长(秒)
            sample_count: 生成视频数量(1-4)
            aspect_ratio: 宽高比(16:9或9:16)
            generate_audio: 是否生成音频
            image_uri: 图片URL(与image_base64二选一)
            image_base64: 图片Base64编码(与image_uri二选一)
            image_mime_type: 图片MIME类型
            resolution: 分辨率(720p或1080p，仅Veo 3支持)
            seed: 随机种子(0-4294967295)
            negative_prompt: 负面提示词
            person_generation: 人物生成控制

        Returns:
            任务ID或直接生成的视频结果
        """
        url = self._build_create_video_url()

        if self._is_chat_completions_endpoint(url):
            text_prompt = prompt.strip()
            if negative_prompt:
                text_prompt = f"{text_prompt}\n\n负面提示词：{negative_prompt.strip()}"

            message_content = [
                {
                    'type': 'text',
                    'text': text_prompt,
                }
            ]

            image_url = image_uri.get('url') if isinstance(image_uri, dict) else image_uri
            if not image_url and image_base64:
                image_url = f'data:{image_mime_type};base64,{image_base64}'

            if image_url:
                message_content.append(
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_url,
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
                raise Exception(f"创建视频任务失败: {str(e)}")

        instance = {"prompt": prompt}

        if image_uri or image_base64:
            image_data = {"mimeType": image_mime_type}
            if image_uri:
                image_data["uri"] = image_uri.get("url", image_uri)
            if image_base64:
                image_data["bytesBase64Encoded"] = image_base64
            instance["image"] = image_data

        parameters = {
            "durationSeconds": duration_seconds,
            "sampleCount": sample_count,
            "aspectRatio": aspect_ratio,
            "personGeneration": person_generation
        }

        if generate_audio and model != "veo-2.0-generate-001":
            parameters["generateAudio"] = generate_audio
        if resolution:
            parameters["resolution"] = resolution
        if seed is not None:
            parameters["seed"] = seed
        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt

        file_path = image_uri.get("url") if isinstance(image_uri, dict) else image_uri

        payload = {
            "width": 720,
            "height": 1280,
            "model": model,
            "prompt": prompt,
            "filePaths": [file_path] if file_path else []
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            print(result)
            data = result.get("data")
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("task_id") or data.get("id") or data
            return result.get("task_id") or result.get("id") or data
        except requests.exceptions.RequestException as e:
            raise Exception(f"创建视频任务失败: {str(e)}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询视频生成任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务详情
        """
        url = self._build_task_status_url(task_id)

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"查询任务状态失败: {str(e)}")

    def wait_for_completion(
        self,
        task_id: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """轮询等待任务完成

        Args:
            task_id: 任务ID
            poll_interval: 轮询间隔(秒)
            max_wait_time: 最大等待时间(秒)
            callback: 状态更新回调函数

        Returns:
            完成后的任务详情
        """
        start_time = time.time()

        while True:
            elapsed_time = time.time() - start_time

            if elapsed_time > max_wait_time:
                raise TimeoutError(f"任务超时: 等待时间超过 {max_wait_time} 秒")

            task_info = self.get_task_status(task_id)
            status = task_info.get("status")

            if callback:
                callback(task_info)

            if status == TaskStatus.COMPLETED.value:
                return task_info
            if status == TaskStatus.FAILED.value:
                message = task_info.get("message", "未知错误")
                raise Exception(f"任务失败: {message}")

            time.sleep(poll_interval)

    def _generate_video(
        self,
        prompt: str,
        poll_interval: int = 5,
        max_wait_time: int = 600,
        **kwargs
    ) -> List[str]:
        """同步生成视频(提交任务并等待完成)

        Args:
            prompt: 视频生成提示词
            poll_interval: 轮询间隔(秒)
            max_wait_time: 最大等待时间(秒)
            **kwargs: 其他参数传递给create_video_task

        Returns:
            视频下载链接列表
        """
        task_result = self.create_video_task(prompt, **kwargs)

        if isinstance(task_result, list):
            video_urls = []
            for item in task_result:
                url = item.get("url") if isinstance(item, dict) else item
                if url:
                    video_urls.append(url)
            print(f"✓ 视频生成完成! 共 {len(video_urls)} 个视频")
            return video_urls

        task_id = task_result
        if isinstance(task_result, dict):
            task_id = task_result.get("task_id") or task_result.get("id")

        print(f"✓ 任务已创建: {task_id}")

        def status_callback(task_info):
            status = task_info.get("status")
            message = task_info.get("message", "")
            print(f"  状态: {status} {message}")

        result = self.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            max_wait_time=max_wait_time,
            callback=status_callback
        )

        videos = result.get("data", {}).get("videos", [])
        video_urls = [video["url"] for video in videos]

        print(f"✓ 视频生成完成! 共 {len(video_urls)} 个视频")
        return video_urls
