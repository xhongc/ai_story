#!/usr/bin/env python3
"""
AI Story CLI - 纯后端命令行入口
使用本地 oMLX (Qwen3.5-9B) + ComfyUI 进行故事视频生成

用法:
    python cli.py --topic "一个勇敢的小骑士"
    python cli.py --interactive
    python cli.py --test-llm
    python cli.py --test-comfyui
"""

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置路径
BASE_DIR = Path(__file__).parent
WORKFLOW_DIR = BASE_DIR / "workflows"


class Config:
    """本地模型配置"""

    # oMLX LLM 配置
    OMLX_API_URL = "http://192.168.1.50:8080/v1"
    OMLX_API_KEY = "niuniuai.apikey"
    OMLX_MODEL = "Qwen3.5-9B-MLX-4bit"

    # ComfyUI 配置
    COMFYUI_API_URL = "http://192.168.1.37:8000"
    COMFYUI_SERVER = "192.168.1.37:8000"

    # 路径配置
    WORKFLOW_FILE = WORKFLOW_DIR / "z_image_t2i_lora_style.json"

    # 输出配置
    OUTPUT_DIR = BASE_DIR / "output"
    IMAGE_OUTPUT_DIR = OUTPUT_DIR / "images"
    VIDEO_OUTPUT_DIR = OUTPUT_DIR / "videos"


def setup_argparse() -> argparse.ArgumentParser:
    """设置命令行参数"""
    parser = argparse.ArgumentParser(
        description="AI Story CLI - 本地AI故事生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --topic "一个勇敢的小骑士探索神秘森林"
  %(prog)s --interactive
  %(prog)s --test-llm
  %(prog)s --test-comfyui
  %(prog)s --generate-only "少女在樱花树下跳舞" --style anime
        """
    )

    parser.add_argument(
        "--topic", "-t",
        type=str,
        help="故事主题"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式"
    )

    parser.add_argument(
        "--test-llm",
        action="store_true",
        help="测试 oMLX LLM 连接"
    )

    parser.add_argument(
        "--test-comfyui",
        action="store_true",
        help="测试 ComfyUI 连接"
    )

    parser.add_argument(
        "--generate-only",
        type=str,
        help="只生成图像，指定提示词"
    )

    parser.add_argument(
        "--style",
        type=str,
        default="anime",
        choices=["anime", "realistic", "cartoon", "oil_painting"],
        help="图像风格 (默认: anime)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出目录"
    )

    parser.add_argument(
        "--workflow",
        type=str,
        help="自定义 ComfyUI workflow JSON 文件路径"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )

    return parser


async def test_llm_connection():
    """测试 oMLX LLM 连接"""
    from core.ai_client.omlx_client import oMLXClient

    print("\n" + "="*60)
    print("🧪 测试 oMLX LLM 连接")
    print("="*60)

    config = Config()
    client = oMLXClient(
        api_url=config.OMLX_API_URL,
        api_key=config.OMLX_API_KEY,
        model_name=config.OMLX_MODEL,
        timeout=60
    )

    # 健康检查
    print(f"\n📡 服务器: {config.OMLX_API_URL}")
    health = client.health_check()
    print(f"   状态: {health['status']}")
    if 'latency_ms' in health:
        print(f"   延迟: {health['latency_ms']}ms")
    if 'models' in health:
        print(f"   可用模型: {', '.join(health.get('models', []))}")

    # 测试生成
    print("\n📝 测试文本生成...")
    print(f"   提示词: '请用一句话介绍自己'")

    response = await client.generate(
        prompt="请用一句话介绍自己",
        max_tokens=200,
        temperature=0.7
    )

    if response.success:
        print(f"\n✅ 生成成功!")
        print(f"   响应: {response.text[:200]}...")
        print(f"   延迟: {response.metadata.get('latency_ms', 'N/A')}ms")
        print(f"   Token数: {response.metadata.get('tokens_used', 'N/A')}")
    else:
        print(f"\n❌ 生成失败: {response.error}")

    return response.success


async def test_comfyui_connection():
    """测试 ComfyUI 连接"""
    from core.ai_client.comfyui_client import ComfyUIClient

    print("\n" + "="*60)
    print("🧪 测试 ComfyUI 连接")
    print("="*60)

    config = Config()
    client = ComfyUIClient(
        api_url=config.COMFYUI_API_URL,
        api_key="",
        model_name="default",
        timeout=300
    )

    # 验证配置
    print(f"\n📡 服务器: {config.COMFYUI_API_URL}")
    is_valid = client.validate_config()
    print(f"   配置有效: {is_valid}")

    if is_valid:
        print("\n✅ ComfyUI 服务正常!")
    else:
        print("\n❌ ComfyUI 服务连接失败!")

    return is_valid


async def generate_image(prompt: str, style: str = "anime", workflow_path: str = None):
    """生成单张图片"""
    from core.ai_client.comfyui_client import ComfyUIClient

    print("\n" + "="*60)
    print("🖼️  生成图像")
    print("="*60)

    config = Config()

    # 确定 workflow 文件
    if workflow_path:
        wf_path = Path(workflow_path)
    else:
        wf_path = config.WORKFLOW_FILE

    if not wf_path.exists():
        print(f"\n❌ Workflow 文件不存在: {wf_path}")
        print("   请确保 workflow JSON 文件存在")
        return None

    # 读取 workflow
    with open(wf_path, 'r', encoding='utf-8') as f:
        workflow_template = json.load(f)

    print(f"\n📁 Workflow: {wf_path.name}")

    # 构建提示词
    full_prompt = f"{prompt}, {style} style"
    print(f"\n🎨 提示词: {full_prompt}")

    # 将提示词注入到 workflow 的 TextEncode 节点
    workflow_data = workflow_template.get('prompt', workflow_template)
    prompt_injected = False
    
    # 查找 TextEncodeZImageOmni 节点并注入提示词
    for node_id, node in workflow_data.items():
        if node.get('class_type') == 'TextEncodeZImageOmni':
            # 获取当前节点的 prompt
            node_inputs = node.get('inputs', {})
            current_prompt = node_inputs.get('prompt', '')
            
            # 如果当前 prompt 不是负面提示词（负面提示词通常包含"模糊"、"低清晰度"等）
            if not any(keyword in current_prompt for keyword in ['模糊', '低清晰度', '水印', 'bad', 'low quality']):
                # 替换为新的提示词
                workflow_data[node_id]['inputs']['prompt'] = full_prompt
                print(f"   📝 已注入到节点 {node_id} ({node['class_type']})")
                prompt_injected = True

    if not prompt_injected:
        print("   ⚠️ 未找到 TextEncodeZImageOmni 节点，请检查 workflow 结构")

    # 创建客户端
    client = ComfyUIClient(
        api_url=config.COMFYUI_API_URL,
        api_key="",
        model_name="default",
        timeout=300,
        save_images=True
    )

    # 生成进度回调
    def progress_callback(progress: float):
        bar_length = 30
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r   [{bar}] {progress:.1f}%", end="", flush=True)

    print("\n⏳ 正在生成...")
    
    # 将修改后的 workflow 转为 JSON 字符串
    workflow_json = json.dumps(workflow_data)
    result = client.generate(
        prompt=workflow_json,
        progress_callback=progress_callback
    )

    print()  # 换行

    if result.get('success'):
        print(f"\n✅ 生成成功!")
        images = result.get('data', [])
        for idx, img in enumerate(images):
            print(f"   图像 {idx+1}: {img.get('url')}")
        return result
    else:
        print(f"\n❌ 生成失败: {result.get('error')}")
        return None


async def generate_story(topic: str):
    """生成故事内容"""
    from core.ai_client.omlx_client import oMLXClient

    print("\n" + "="*60)
    print("📖 生成故事")
    print("="*60)

    config = Config()
    client = oMLXClient(
        api_url=config.OMLX_API_URL,
        api_key=config.OMLX_API_KEY,
        model_name=config.OMLX_MODEL,
        timeout=120
    )

    # 故事生成提示词
    story_prompt = f"""请为以下主题创作一个简短的故事脚本:

主题: {topic}

要求:
1. 故事要有起承转合，适合制作短视频
2. 分成3-5个分镜描述
3. 每个分镜包含: 场景描述、旁白文字、画面提示词

请用JSON格式输出:
{{
  "title": "故事标题",
  "scenes": [
    {{
      "scene": "场景1描述",
      "narration": "旁白文字",
      "image_prompt": "图像生成提示词"
    }}
  ]
}}
"""

    print(f"\n⏳ 正在生成故事...")
    print(f"   主题: {topic}")

    # 流式生成
    full_text = ""
    import time
    start = time.time()

    try:
        for chunk in client.generate_stream(prompt=story_prompt, max_tokens=4096):
            if chunk['type'] == 'token':
                content = chunk['content']
                full_text += content
                # 简单打印
                if len(full_text) % 50 == 0:
                    print(".", end="", flush=True)
            elif chunk['type'] == 'done':
                full_text = chunk['full_text']
                break
            elif chunk['type'] == 'error':
                print(f"\n❌ 错误: {chunk['error']}")
                return None

        print(f"\n\n✅ 故事生成完成! ({(time.time()-start):.1f}秒)")

        # 尝试解析JSON
        try:
            # 提取JSON部分
            json_start = full_text.find('{')
            json_end = full_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = full_text[json_start:json_end]
                story_data = json.loads(json_str)
                return story_data
            else:
                print("⚠️  无法解析JSON，返回原始文本")
                return {"text": full_text, "raw": True}

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON解析失败: {e}")
            return {"text": full_text, "raw": True}

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        return None


async def interactive_mode():
    """交互模式"""
    print("\n" + "="*60)
    print("🎭 AI Story 交互模式")
    print("="*60)
    print("\n欢迎使用 AI Story CLI!")
    print("输入 'help' 查看命令, 'exit' 退出\n")

    while True:
        try:
            cmd = input("\n> ").strip()

            if not cmd:
                continue

            if cmd.lower() in ['exit', 'quit', 'q']:
                print("👋 再见!")
                break

            elif cmd.lower() in ['help', 'h', '?']:
                print("""
可用命令:
  topic <主题>     - 根据主题生成故事
  image <提示词>   - 生成图像
  test             - 测试连接
  help             - 显示帮助
  exit             - 退出
                """)
            elif cmd.lower().startswith('topic '):
                topic = cmd[6:].strip()
                await generate_story(topic)

            elif cmd.lower().startswith('image '):
                prompt = cmd[6:].strip()
                await generate_image(prompt)

            elif cmd.lower() == 'test':
                await test_llm_connection()
                await test_comfyui_connection()

            else:
                print("❓ 未知命令，输入 'help' 查看帮助")

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


async def main_async(args):
    """异步主函数"""
    # 确保输出目录存在
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Config.IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.test_llm:
        success = await test_llm_connection()
        return 0 if success else 1

    if args.test_comfyui:
        success = await test_comfyui_connection()
        return 0 if success else 1

    if args.interactive:
        await interactive_mode()
        return 0

    if args.generate_only:
        result = await generate_image(args.generate_only, args.style, args.workflow)
        return 0 if result else 1

    if args.topic:
        # 生成完整故事流程
        print("\n" + "🎬"*30)
        print("AI Story 本地生成器")
        print("🎬"*30)

        # 1. 生成故事
        story = await generate_story(args.topic)
        if not story:
            return 1

        print("\n" + "-"*60)
        print("📜 生成的故事:")
        print("-"*60)
        if story.get('raw'):
            print(story.get('text', ''))
        else:
            print(json.dumps(story, indent=2, ensure_ascii=False))

        # 2. 询问是否生成图像
        if not story.get('raw') and story.get('scenes'):
            print("\n" + "-"*60)
            scenes = story.get('scenes', [])
            print(f"📷 检测到 {len(scenes)} 个场景，是否生成图像? (y/n)")

            try:
                response = input("> ").strip().lower()
                if response in ['y', 'yes', '是']:
                    for idx, scene in enumerate(scenes):
                        print(f"\n[{idx+1}/{len(scenes)}] 生成: {scene.get('scene', '场景')[:30]}...")
                        image_prompt = scene.get('image_prompt', scene.get('scene', ''))
                        await generate_image(image_prompt, args.style, args.workflow)
            except KeyboardInterrupt:
                print("\n\n👋 已取消")

        return 0

    # 无参数，显示帮助
    return 0


def main():
    """主入口"""
    parser = setup_argparse()
    args = parser.parse_args()

    if args.verbose:
        print(f"📁 基础目录: {Config.BASE_DIR}")
        print(f"📁 Workflow: {Config.WORKFLOW_FILE}")
        print(f"📁 输出目录: {Config.OUTPUT_DIR}")
        print()

    try:
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 已取消")
        sys.exit(0)


if __name__ == "__main__":
    main()
