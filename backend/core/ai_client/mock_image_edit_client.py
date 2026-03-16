"""
Mock 图片编辑客户端实现
用于测试和开发环境，返回模拟的图片URL
"""

import time

from .base import ImageEditClient, AIResponse


class MockImageEditClient(ImageEditClient):
    """Mock 图片编辑客户端"""

    def _edit_image(
        self,
        image_url: str,
        prompt: str = "",
        mask_url: str = "",
        strength: float = 0.35,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> AIResponse:
        start_time = time.time()
        time.sleep(1.0)

        seed = abs(hash(f'{image_url}:{prompt}:{strength}:{width}:{height}')) % 10000
        edited_url = f'https://picsum.photos/{width}/{height}?random={seed}'
        latency_ms = int((time.time() - start_time) * 1000)

        return AIResponse(
            success=True,
            text='Mock image edit completed',
            data=[{
                'url': edited_url,
                'width': width,
                'height': height,
                'source_image_url': image_url,
                'mask_url': mask_url,
            }],
            metadata={
                'latency_ms': latency_ms,
                'model': self.model_name,
                'strength': strength,
                'is_mock': True,
            }
        )

    async def validate_config(self) -> bool:
        return True
