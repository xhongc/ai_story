"""
执行器注册表
职责: 管理AI客户端执行器的动态导入和验证
遵循开闭原则(OCP): 支持动态扩展新执行器
"""

import importlib
from typing import Type, Optional
from .base import BaseAIClient, LLMClient, Text2ImageClient, Image2VideoClient, ImageEditClient


def get_executor_class(class_path: str) -> Optional[Type[BaseAIClient]]:
    """
    根据类路径字符串动态导入执行器类

    Args:
        class_path: 完整的类路径，如 'core.ai_client.openai_client.OpenAIClient'

    Returns:
        Type[BaseAIClient]: 执行器类对象

    Raises:
        ImportError: 无法导入指定的类
        AttributeError: 类路径格式错误
    """
    if not class_path:
        raise ValueError("执行器类路径不能为空")

    try:
        # 分割模块路径和类名
        module_path, class_name = class_path.rsplit('.', 1)

        # 动态导入模块
        module = importlib.import_module(module_path)

        # 获取类对象
        executor_class = getattr(module, class_name)

        return executor_class

    except (ImportError, AttributeError) as e:
        raise ImportError(f"无法导入执行器类 '{class_path}': {str(e)}")


def validate_executor(executor_class: Type, expected_base_class: Type[BaseAIClient]) -> bool:
    """
    验证执行器类是否继承自指定的基类

    Args:
        executor_class: 执行器类
        expected_base_class: 期望的基类（LLMClient, Text2ImageClient, Image2VideoClient）

    Returns:
        bool: 是否有效
    """
    if not executor_class:
        return False

    # 检查是否是类
    if not isinstance(executor_class, type):
        return False

    # 检查是否继承自指定基类
    return issubclass(executor_class, expected_base_class)


def get_base_class_for_provider_type(provider_type: str) -> Type[BaseAIClient]:
    """
    根据provider_type获取对应的基类

    Args:
        provider_type: 提供商类型 ('llm', 'text2image', 'image2video')

    Returns:
        Type[BaseAIClient]: 对应的基类

    Raises:
        ValueError: 无效的provider_type
    """
    base_class_map = {
        'llm': LLMClient,
        'text2image': Text2ImageClient,
        'image2video': Image2VideoClient,
        'image_edit': ImageEditClient,
    }

    base_class = base_class_map.get(provider_type)

    if not base_class:
        raise ValueError(f"无效的provider_type: {provider_type}")

    return base_class


def validate_executor_for_provider(
    executor_class: Type,
    provider_type: str
) -> bool:
    """
    验证执行器类是否适用于指定的provider_type

    Args:
        executor_class: 执行器类
        provider_type: 提供商类型

    Returns:
        bool: 是否有效
    """
    try:
        expected_base_class = get_base_class_for_provider_type(provider_type)
        return validate_executor(executor_class, expected_base_class)
    except ValueError:
        return False
