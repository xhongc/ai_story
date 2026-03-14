#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成API客户端
支持视频生成任务提交和轮询查询
"""

import requests
import time
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    INITIALIZING = "Initializing"
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    UPLOADING = "Uploading"
    UNKNOWN = "Unknown"


class VideoGenerator:
    """视频生成客户端"""


    def __init__(self, api_url:str ,api_token: str, model: str):
        """初始化视频生成客户端

        Args:
            api_token: API认证令牌
            use_backup: 是否使用备用URL
        """
        self.api_token = api_token
        self.base_url = api_url
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

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
    ) -> str:
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
            任务ID
        """
        url = f"{self.base_url}/v1/videos/generations"

        # 构建请求体
        instance = {"prompt": prompt}

        # 添加图片信息(如果提供)
        if image_uri or image_base64:
            image_data = {"mimeType": image_mime_type}
            if image_uri:
                image_data["uri"] = image_uri.get("url", image_uri)
            if image_base64:
                image_data["bytesBase64Encoded"] = image_base64
            instance["image"] = image_data

        # 构建参数
        parameters = {
            "durationSeconds": duration_seconds,
            "sampleCount": sample_count,
            "aspectRatio": aspect_ratio,
            "personGeneration": person_generation
        }

        # 添加可选参数
        if generate_audio and model != "veo-2.0-generate-001":
            parameters["generateAudio"] = generate_audio
        if resolution:
            parameters["resolution"] = resolution
        if seed is not None:
            parameters["seed"] = seed
        if negative_prompt:
            parameters["negativePrompt"] = negative_prompt

        # payload = {
        #     "instances": [instance],
        #     "parameters": parameters,
        #     "model": model
        # }
        payload = {
            "width": 720,
            "height": 1280,
            "model": model,
            "prompt": prompt,
            "filePaths": [image_uri.get("url")]
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            print(result)
            return result["data"] # [{"url": "xx"}]
        except requests.exceptions.RequestException as e:
            raise Exception(f"创建视频任务失败: {str(e)}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """查询视频生成任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务详情
        """
        url = f"{self.base_url}/v1/videos/generations/{task_id}"

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

            # 执行回调
            if callback:
                callback(task_info)

            # 检查任务状态
            if status == TaskStatus.COMPLETED.value:
                return task_info
            elif status == TaskStatus.FAILED.value:
                message = task_info.get("message", "未知错误")
                raise Exception(f"任务失败: {message}")

            # 等待后继续轮询
            time.sleep(poll_interval)

    def generate_video_sync(
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
        # 创建任务
        task_id = self.create_video_task(prompt, **kwargs)
        print(f"✓ 任务已创建: {task_id}")

        # 状态回调
        def status_callback(task_info):
            status = task_info.get("status")
            message = task_info.get("message", "")
            print(f"  状态: {status} {message}")

        # 等待完成
        result = self.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            max_wait_time=max_wait_time,
            callback=status_callback
        )

        # 提取视频链接
        videos = result.get("data", {}).get("videos", [])
        video_urls = [video["url"] for video in videos]

        print(f"✓ 视频生成完成! 共 {len(video_urls)} 个视频")
        return video_urls

