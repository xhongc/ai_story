#!/usr/bin/env python
"""
验证数据流转是否正常的脚本
用于测试优化后的数据存储方案
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.projects.models import Project
from apps.content.models import ContentRewrite, Storyboard, CameraMovement, GeneratedImage
from django.contrib.auth import get_user_model

User = get_user_model()


def verify_data_flow():
    """验证数据流转"""
    print("=" * 60)
    print("开始验证数据流转...")
    print("=" * 60)

    # 1. 检查是否有项目
    projects = Project.objects.all()
    print(f"\n1. 项目总数: {projects.count()}")

    if projects.count() == 0:
        print("   ⚠️  没有找到项目,无法验证数据流转")
        return

    # 选择第一个项目进行验证
    project = projects.first()
    print(f"   选择项目: {project.name} (ID: {project.id})")

    # 2. 检查文案改写数据
    print(f"\n2. 文案改写数据:")
    try:
        content_rewrite = ContentRewrite.objects.get(project=project)
        print(f"   ✅ 找到文案改写记录")
        print(f"      - 原始文本长度: {len(content_rewrite.original_text)}")
        print(f"      - 改写后文本长度: {len(content_rewrite.rewritten_text)}")
        print(f"      - 使用的模型: {content_rewrite.model_provider.model_name if content_rewrite.model_provider else '未设置'}")
        print(f"      - 创建时间: {content_rewrite.created_at}")
    except ContentRewrite.DoesNotExist:
        print(f"   ⚠️  未找到文案改写记录")

    # 3. 检查分镜数据
    print(f"\n3. 分镜数据:")
    storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')
    print(f"   分镜总数: {storyboards.count()}")

    if storyboards.count() > 0:
        print(f"   ✅ 找到 {storyboards.count()} 个分镜")
        for sb in storyboards[:3]:  # 只显示前3个
            print(f"      - 分镜 {sb.sequence_number}:")
            print(f"        场景描述: {sb.scene_description[:50]}...")
            print(f"        旁白: {sb.narration_text[:50]}...")
            print(f"        使用的模型: {sb.model_provider.model_name if sb.model_provider else '未设置'}")
        if storyboards.count() > 3:
            print(f"      ... 还有 {storyboards.count() - 3} 个分镜")
    else:
        print(f"   ⚠️  未找到分镜记录")

    # 4. 检查生成的图片
    print(f"\n4. 生成的图片:")
    images = GeneratedImage.objects.filter(storyboard__project=project)
    print(f"   图片总数: {images.count()}")

    if images.count() > 0:
        print(f"   ✅ 找到 {images.count()} 张图片")
        for img in images[:3]:  # 只显示前3张
            print(f"      - 分镜 {img.storyboard.sequence_number} 的图片:")
            print(f"        URL: {img.image_url[:60]}...")
            print(f"        尺寸: {img.width}x{img.height}")
            print(f"        状态: {img.get_status_display()}")
            print(f"        使用的模型: {img.model_provider.model_name if img.model_provider else '未设置'}")
        if images.count() > 3:
            print(f"      ... 还有 {images.count() - 3} 张图片")
    else:
        print(f"   ⚠️  未找到图片记录")

    # 5. 检查运镜数据
    print(f"\n5. 运镜数据:")
    camera_movements = CameraMovement.objects.filter(storyboard__project=project)
    print(f"   运镜总数: {camera_movements.count()}")

    if camera_movements.count() > 0:
        print(f"   ✅ 找到 {camera_movements.count()} 个运镜")
        for cm in camera_movements[:3]:  # 只显示前3个
            print(f"      - 分镜 {cm.storyboard.sequence_number} 的运镜:")
            print(f"        运镜类型: {cm.get_movement_type_display() if cm.movement_type else '未设置'}")
            print(f"        使用的模型: {cm.model_provider.model_name if cm.model_provider else '未设置'}")
        if camera_movements.count() > 3:
            print(f"      ... 还有 {camera_movements.count() - 3} 个运镜")
    else:
        print(f"   ⚠️  未找到运镜记录")

    # 6. 数据完整性检查
    print(f"\n6. 数据完整性检查:")
    print(f"   检查分镜是否都有对应的图片...")

    storyboards_with_images = 0
    storyboards_without_images = 0

    for sb in storyboards:
        if sb.images.exists():
            storyboards_with_images += 1
        else:
            storyboards_without_images += 1

    print(f"   - 有图片的分镜: {storyboards_with_images}")
    print(f"   - 无图片的分镜: {storyboards_without_images}")

    if storyboards_without_images == 0 and storyboards.count() > 0:
        print(f"   ✅ 所有分镜都有对应的图片")
    elif storyboards.count() > 0:
        print(f"   ⚠️  有 {storyboards_without_images} 个分镜没有图片")

    print(f"\n   检查分镜是否都有对应的运镜...")

    storyboards_with_camera = 0
    storyboards_without_camera = 0

    for sb in storyboards:
        try:
            _ = sb.camera_movement
            storyboards_with_camera += 1
        except CameraMovement.DoesNotExist:
            storyboards_without_camera += 1

    print(f"   - 有运镜的分镜: {storyboards_with_camera}")
    print(f"   - 无运镜的分镜: {storyboards_without_camera}")

    if storyboards_without_camera == 0 and storyboards.count() > 0:
        print(f"   ✅ 所有分镜都有对应的运镜")
    elif storyboards.count() > 0:
        print(f"   ⚠️  有 {storyboards_without_camera} 个分镜没有运镜")

    print("\n" + "=" * 60)
    print("验证完成!")
    print("=" * 60)


if __name__ == '__main__':
    verify_data_flow()
