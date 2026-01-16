"""
Mock LLM 客户端实现
用于测试和开发环境，返回模拟的 LLM 响应
"""

import time
import json
from typing import Dict, Any, Generator
from .base import LLMClient, AIResponse


class MockLLMClient(LLMClient):
    """
    Mock LLM 客户端
    返回预定义的模拟响应，用于测试工作流
    """

    # 模拟响应模板
    MOCK_RESPONSES = {
        "rewrite": """经过改写的故事内容：

在一个宁静的小镇上，住着一位年轻的画家。每天清晨，他都会来到河边，用画笔记录下大自然的美丽瞬间。

这个故事讲述了艺术与生活的完美融合，展现了一个追梦者的日常。通过细腻的笔触，我们看到了他对艺术的执着追求。

改写后的内容更加生动，情感更加饱满，适合进行下一步的分镜创作。""",

        "storyboard": """[
  {
    "scene_number": 1,
    "scene_description": "清晨的小镇，阳光洒在石板路上",
    "narration_text": "在一个宁静的小镇上，新的一天开始了",
    "image_prompt": "A peaceful small town at dawn, sunlight on cobblestone streets, warm golden light, cinematic composition, high quality",
    "duration_seconds": 3,
    "camera_movement": "static"
  },
  {
    "scene_number": 2,
    "scene_description": "年轻画家背着画板走向河边",
    "narration_text": "年轻的画家像往常一样，带着他的画具出门了",
    "image_prompt": "A young artist walking towards a river, carrying an easel and painting supplies, morning light, artistic atmosphere, detailed",
    "duration_seconds": 4,
    "camera_movement": "follow"
  },
  {
    "scene_number": 3,
    "scene_description": "河边美景，画家开始作画",
    "narration_text": "他在河边架起画架，开始捕捉大自然的美丽",
    "image_prompt": "Artist painting by a beautiful river, easel setup, natural scenery, peaceful atmosphere, professional photography",
    "duration_seconds": 5,
    "camera_movement": "slow_zoom_in"
  }
]""",

        "camera_movement": """{
  "movement_type": "slow_zoom_in",
  "movement_params": {
    "start_scale": 1.0,
    "end_scale": 1.2,
    "duration": 3.0,
    "easing": "ease_in_out"
  },
  "description": "缓慢推进镜头，聚焦主体"
}""",

        "default": """这是一个模拟的 LLM 响应。

在实际使用中，这里会返回根据提示词生成的真实内容。Mock API 主要用于：
1. 开发环境的快速测试
2. 工作流程的验证
3. 前端界面的调试
4. 成本控制（避免频繁调用真实 API）

请在生产环境中配置真实的 LLM 服务。"""
    }

    async def _generate_text(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> AIResponse:
        """
        生成模拟的文本响应

        Args:
            prompt: 输入提示词
            max_tokens: 最大token数（Mock中忽略）
            temperature: 温度参数（Mock中忽略）
            **kwargs: 其他参数

        Returns:
            AIResponse: 模拟响应对象
        """
        start_time = time.time()

        # 模拟API延迟
        time.sleep(0.5)

        # 根据提示词内容判断响应类型
        response_text = self._get_mock_response(prompt)

        # 模拟token使用量
        tokens_used = len(response_text) // 4  # 粗略估算

        latency_ms = int((time.time() - start_time) * 1000)

        return AIResponse(
            success=True,
            text=response_text,
            metadata={
                'tokens_used': tokens_used,
                'latency_ms': latency_ms,
                'model': self.model_name,
                'is_mock': True
            }
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式生成模拟文本

        Args:
            prompt: 输入提示词
            system_prompt: 系统提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Yields:
            Dict包含: type (token/done/error), content, metadata
        """
        start_time = time.time()

        # 获取模拟响应
        response_text = self._get_mock_response(prompt)

        # 模拟流式输出，每次返回几个字符
        chunk_size = 10
        full_text = ""

        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            full_text += chunk

            # 模拟网络延迟
            time.sleep(0.05)

            yield {
                'type': 'token',
                'content': chunk,
                'full_text': full_text
            }

        # 发送完成信号
        latency_ms = int((time.time() - start_time) * 1000)

        yield {
            'type': 'done',
            'full_text': full_text,
            'metadata': {
                'latency_ms': latency_ms,
                'model': self.model_name,
                'finish_reason': 'stop',
                'is_mock': True
            }
        }

    def _get_mock_response(self, prompt: str) -> str:
        """
        根据提示词内容返回相应的模拟响应

        Args:
            prompt: 输入提示词

        Returns:
            str: 模拟响应文本
        """
        prompt_lower = prompt.lower()

        # 根据关键词判断响应类型
        if any(keyword in prompt_lower for keyword in ['改写', 'rewrite', '润色', '优化文案']):
            return self.MOCK_RESPONSES['rewrite']
        elif any(keyword in prompt_lower for keyword in ['分镜', 'storyboard', '场景', 'scene']):
            return self.MOCK_RESPONSES['storyboard']
        elif any(keyword in prompt_lower for keyword in ['运镜', 'camera', '镜头', 'movement']):
            return self.MOCK_RESPONSES['camera_movement']
        else:
            return self.MOCK_RESPONSES['default']

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
