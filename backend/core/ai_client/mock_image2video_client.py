"""
Mock 图生视频客户端实现
用于测试和开发环境，返回模拟的视频URL
"""

import time
from typing import Dict, Any
from .base import Image2VideoClient, AIResponse


class MockImage2VideoClient(Image2VideoClient):
    """
    Mock 图生视频客户端
    返回预定义的模拟视频URL，用于测试工作流
    """

    # 模拟视频URL列表（使用示例视频）
    MOCK_VIDEO_URLS = [
        "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
    ]

    async def _generate_video(
        self,
        image_url: str,
        camera_movement: Dict[str, Any],
        duration: float,
        fps: int,
        **kwargs
    ) -> AIResponse:
        """
        生成模拟的视频响应

        Args:
            image_url: 源图片URL
            camera_movement: 运镜参数
            duration: 视频时长
            fps: 帧率
            **kwargs: 其他参数

        Returns:
            AIResponse: 包含模拟视频URL的响应对象
        """
        start_time = time.time()

        # 模拟API延迟（视频生成通常很慢）
        time.sleep(2.0)

        # 从kwargs获取参数
        width = kwargs.get('width', 1280)
        height = kwargs.get('height', 720)
        model = kwargs.get('model', self.model_name)

        # 根据图片URL哈希选择视频（保证相同图片返回相同视频）
        image_hash = hash(image_url) % len(self.MOCK_VIDEO_URLS)
        video_url = self.MOCK_VIDEO_URLS[image_hash]

        # 构建视频数据
        video_data = {
            "url": video_url,
            "width": width,
            "height": height,
            "duration": duration,
            "fps": fps,
            "format": "mp4",
            "file_size": 1024 * 1024,  # 模拟1MB文件大小
            "camera_movement": camera_movement
        }

        latency_ms = int((time.time() - start_time) * 1000)

        return AIResponse(
            success=True,
            data={
                'url': video_url,
                'video': video_data,
                'videos': [video_data]  # 兼容多视频格式
            },
            metadata={
                'latency_ms': latency_ms,
                'model': model,
                'is_mock': True,
                'source_image': image_url[:100]  # 记录部分源图片URL
            }
        )

    async def validate_config(self) -> bool:
        """
        验证配置（Mock客户端始终返回True）

        Returns:
            bool: 始终返回True
        """
        return True

    async def health_check(self) -> bool:
        """
        健康检查（Mock客户端始终返回True）

        Returns:
            bool: 始终返回True
        """
        return True
