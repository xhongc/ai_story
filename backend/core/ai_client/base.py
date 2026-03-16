"""
AI客户端抽象基类
遵循依赖倒置原则(DIP): 定义抽象接口,具体实现依赖接口
遵循开闭原则(OCP): 对扩展开放,对修改封闭
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AIResponse:
    """AI响应统一数据结构"""

    success: bool
    text: str = ""
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}


class BaseAIClient(ABC):
    """
    AI客户端抽象基类
    所有AI客户端必须实现此接口
    """

    def __init__(self, api_url: str, api_key: str, model_name: str, **kwargs):
        """
        初始化客户端

        Args:
            api_url: API地址
            api_key: API密钥
            model_name: 模型名称
            **kwargs: 其他配置参数
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.config = kwargs

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        生成内容

        Args:
            prompt: 输入提示词
            **kwargs: 其他参数

        Returns:
            AIResponse: 统一响应对象
        """
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        pass

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 服务是否健康
        """
        try:
            return await self.validate_config()
        except Exception:
            return False


class LLMClient(BaseAIClient):
    """
    LLM客户端抽象基类
    用于文案改写、分镜生成、运镜生成等文本生成任务
    """

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> AIResponse:
        """
        生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            AIResponse: 响应对象
        """
        return await self._generate_text(prompt, max_tokens, temperature, **kwargs)

    @abstractmethod
    async def _generate_text(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> AIResponse:
        """具体的文本生成实现"""
        pass


class Text2ImageClient(BaseAIClient):
    """
    文生图客户端抽象基类
    """

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        **kwargs
    ) -> AIResponse:
        """
        生成图片

        Args:
            prompt: 图片提示词
            negative_prompt: 负面提示词
            width: 宽度
            height: 高度
            steps: 生成步数
            **kwargs: 其他参数

        Returns:
            AIResponse: 包含图片URL的响应对象
        """
        return self._generate_image(
            prompt, negative_prompt, width, height, steps, **kwargs
        )

    @abstractmethod
    def _generate_image(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        **kwargs
    ) -> AIResponse:
        """具体的图片生成实现"""
        pass


class Image2VideoClient(BaseAIClient):
    """
    图生视频客户端抽象基类
    """

    async def generate(
        self,
        image_url: str,
        camera_movement: Dict[str, Any],
        duration: float = 3.0,
        fps: int = 24,
        **kwargs
    ) -> AIResponse:
        """
        生成视频

        Args:
            image_url: 源图片URL
            camera_movement: 运镜参数
            duration: 视频时长
            fps: 帧率
            **kwargs: 其他参数

        Returns:
            AIResponse: 包含视频URL的响应对象
        """
        return await self._generate_video(
            image_url, camera_movement, duration, fps, **kwargs
        )

    @abstractmethod
    async def _generate_video(
        self,
        image_url: str,
        camera_movement: Dict[str, Any],
        duration: float,
        fps: int,
        **kwargs
    ) -> AIResponse:
        """具体的视频生成实现"""
        pass


class ImageEditClient(BaseAIClient):
    """
    图片编辑客户端抽象基类
    """

    def generate(
        self,
        image_url: str,
        prompt: str = "",
        mask_url: str = "",
        strength: float = 0.35,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> AIResponse:
        """
        编辑图片

        Args:
            image_url: 源图片地址
            prompt: 编辑提示词
            mask_url: 蒙版图片地址
            strength: 重绘强度
            width: 输出宽度
            height: 输出高度
            **kwargs: 其他参数

        Returns:
            AIResponse: 包含编辑后图片URL的响应对象
        """
        return self._edit_image(
            image_url=image_url,
            prompt=prompt,
            mask_url=mask_url,
            strength=strength,
            width=width,
            height=height,
            **kwargs
        )

    @abstractmethod
    def _edit_image(
        self,
        image_url: str,
        prompt: str,
        mask_url: str,
        strength: float,
        width: int,
        height: int,
        **kwargs
    ) -> AIResponse:
        """具体的图片编辑实现"""
        pass
