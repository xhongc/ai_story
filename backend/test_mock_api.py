#!/usr/bin/env python
"""
Mock API 客户端测试脚本
测试所有 Mock 客户端的功能
"""

import os
import sys
import django
import asyncio

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from core.ai_client.mock_llm_client import MockLLMClient
from core.ai_client.mock_text2image_client import MockText2ImageClient
from core.ai_client.mock_image2video_client import MockImage2VideoClient


async def test_mock_llm_client():
    """测试 Mock LLM 客户端"""
    print("\n" + "=" * 60)
    print("测试 Mock LLM 客户端")
    print("=" * 60)

    client = MockLLMClient(
        api_url="http://localhost:8000/api/mock",
        api_key="mock-key",
        model_name="mock-llm-v1"
    )

    # 测试文案改写
    print("\n1. 测试文案改写:")
    response = await client.generate(
        prompt="请改写以下内容：一个年轻人在城市中寻找梦想",
        max_tokens=500
    )
    print(f"  成功: {response.success}")
    print(f"  响应长度: {len(response.text)} 字符")
    print(f"  Token使用: {response.metadata.get('tokens_used')}")
    print(f"  延迟: {response.metadata.get('latency_ms')} ms")
    print(f"  内容预览: {response.text[:100]}...")

    # 测试分镜生成
    print("\n2. 测试分镜生成:")
    response = await client.generate(
        prompt="请生成分镜脚本：一个关于小猫的故事",
        max_tokens=1000
    )
    print(f"  成功: {response.success}")
    print(f"  响应长度: {len(response.text)} 字符")
    print(f"  内容预览: {response.text[:150]}...")

    # 测试运镜生成
    print("\n3. 测试运镜生成:")
    response = await client.generate(
        prompt="请生成运镜参数：一个推进镜头",
        max_tokens=500
    )
    print(f"  成功: {response.success}")
    print(f"  响应长度: {len(response.text)} 字符")
    print(f"  内容预览: {response.text[:100]}...")

    # 测试流式生成
    print("\n4. 测试流式生成:")
    print("  开始流式输出...")
    full_text = ""
    for chunk in client.generate_stream(
        prompt="请生成一段测试文本",
        max_tokens=200
    ):
        if chunk['type'] == 'token':
            full_text += chunk['content']
            print(".", end="", flush=True)
        elif chunk['type'] == 'done':
            print(f"\n  完成! 总长度: {len(full_text)} 字符")
            print(f"  延迟: {chunk['metadata'].get('latency_ms')} ms")

    print("\n✓ Mock LLM 客户端测试通过!")


def test_mock_text2image_client():
    """测试 Mock 文生图客户端"""
    print("\n" + "=" * 60)
    print("测试 Mock 文生图客户端")
    print("=" * 60)

    client = MockText2ImageClient(
        api_url="http://localhost:8000/api/mock",
        api_key="mock-key",
        model_name="mock-text2image-v1"
    )

    # 测试单张图片生成
    print("\n1. 测试单张图片生成:")
    response = client.generate(
        prompt="A beautiful sunset over the ocean",
        width=1024,
        height=1024
    )
    print(f"  成功: {response.success}")
    print(f"  图片数量: {len(response.data.get('urls', []))}")
    print(f"  图片URL: {response.data.get('urls', [])[0]}")
    print(f"  延迟: {response.metadata.get('latency_ms')} ms")

    # 测试多张图片生成
    print("\n2. 测试多张图片生成:")
    response = client.generate(
        prompt="A cute cat playing in the garden",
        width=1024,
        height=1024,
        sample_count=3
    )
    print(f"  成功: {response.success}")
    print(f"  图片数量: {len(response.data.get('urls', []))}")
    for i, url in enumerate(response.data.get('urls', []), 1):
        print(f"  图片 {i}: {url}")

    print("\n✓ Mock 文生图客户端测试通过!")


async def test_mock_image2video_client():
    """测试 Mock 图生视频客户端"""
    print("\n" + "=" * 60)
    print("测试 Mock 图生视频客户端")
    print("=" * 60)

    client = MockImage2VideoClient(
        api_url="http://localhost:8000/api/mock",
        api_key="mock-key",
        model_name="mock-image2video-v1"
    )

    # 测试视频生成
    print("\n1. 测试视频生成:")
    response = await client.generate(
        image_url="https://picsum.photos/1024/1024",
        camera_movement={
            "movement_type": "zoom_in",
            "movement_params": {
                "start_scale": 1.0,
                "end_scale": 1.2,
                "duration": 3.0
            }
        },
        duration=3.0,
        fps=24
    )
    print(f"  成功: {response.success}")
    print(f"  视频URL: {response.data.get('url')}")
    print(f"  视频信息: {response.data.get('video')}")
    print(f"  延迟: {response.metadata.get('latency_ms')} ms")

    print("\n✓ Mock 图生视频客户端测试通过!")


async def test_all():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Mock API 客户端完整测试")
    print("=" * 60)

    try:
        # 测试 LLM 客户端
        await test_mock_llm_client()

        # 测试文生图客户端
        test_mock_text2image_client()

        # 测试图生视频客户端
        await test_mock_image2video_client()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过!")
        print("=" * 60)
        print("\nMock API 配置已就绪，可以用于:")
        print("  1. 开发环境的快速测试")
        print("  2. 工作流程的验证")
        print("  3. 前端界面的调试")
        print("  4. CI/CD 自动化测试")
        print("\n使用方法:")
        print("  - 在模型管理中选择 'Mock LLM API'")
        print("  - 在模型管理中选择 'Mock Text2Image API'")
        print("  - 在模型管理中选择 'Mock Image2Video API'")
        print("  - 在提示词管理中选择 'Mock API 测试模板集'")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_all())
