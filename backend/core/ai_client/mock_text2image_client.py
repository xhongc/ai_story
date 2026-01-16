"""
Mock 文生图客户端实现
用于测试和开发环境，返回模拟的图片URL
"""

import time
from typing import Dict, Any
from .base import Text2ImageClient, AIResponse


class MockText2ImageClient(Text2ImageClient):
    """
    Mock 文生图客户端
    返回预定义的模拟图片URL，用于测试工作流
    """

    # 模拟图片URL列表（使用占位图服务）
    MOCK_IMAGE_URLS = [
        "https://picsum.photos/1024/1024?random=1",
        "https://picsum.photos/1024/1024?random=2",
        "https://picsum.photos/1024/1024?random=3",
        "https://picsum.photos/1024/1024?random=4",
        "https://picsum.photos/1024/1024?random=5",
    ]

    def _generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        **kwargs
    ) -> AIResponse:
        """
        生成模拟的图片响应

        Args:
            prompt: 图片提示词
            negative_prompt: 负面提示词
            width: 宽度
            height: 高度
            steps: 生成步数
            **kwargs: 其他参数

        Returns:
            AIResponse: 包含模拟图片URL的响应对象
        """
        start_time = time.time()

        # 模拟API延迟（图片生成通常较慢）
        time.sleep(1.0)

        # 从kwargs获取参数
        ratio = kwargs.get('ratio', '1:1')
        resolution = kwargs.get('resolution', '2k')
        sample_count = kwargs.get('sample_count', 1)

        # 根据提示词哈希选择图片（保证相同提示词返回相同图片）
        prompt_hash = hash(prompt) % len(self.MOCK_IMAGE_URLS)
        base_url = self.MOCK_IMAGE_URLS[prompt_hash]

        # 生成多张图片（如果需要）
        image_urls = []
        images_data = []

        for i in range(sample_count):
            # 使用不同的随机种子
            url = f"{base_url}&seed={prompt_hash + i}"
            image_urls.append(url)
            images_data.append({
                "url": url,
                "width": width,
                "height": height,
                "format": "jpeg"
            })

        latency_ms = int((time.time() - start_time) * 1000)

        return AIResponse(
            success=True,
            data={
                'urls': image_urls,
                'images': images_data
            },
            metadata={
                'latency_ms': latency_ms,
                'model': self.model_name,
                'ratio': ratio,
                'resolution': resolution,
                'is_mock': True,
                'prompt': prompt[:100]  # 记录部分提示词
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
