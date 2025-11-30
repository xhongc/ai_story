# 导入模块
import os
import pyJianYingDraft as draft
from pyJianYingDraft import IntroType, TransitionType, trange, tim
from pathlib import Path

# 设置草稿文件夹
draft_folder = draft.DraftFolder(r"D:\JianyingPro Drafts")

video_path = r"D:\coding\ai_story\storage\video"
tutorial_asset_dir = r"D:\coding\ai_story\storage\audio"
subtitle_path = r"D:\coding\ai_story\storage\subtitle"  # 字幕文件目录（可选）

# 支持的视频文件格式
SUPPORTED_VIDEO_FORMATS = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
# 支持的字幕文件格式（可选，与视频同名）
SUPPORTED_SUBTITLE_FORMATS = ('.txt', '.srt')

# ---------------------- 函数：获取视频对应的字幕内容 ----------------------
def get_video_subtitle(video_file, subtitle_dir=None):
    """
    获取视频对应的字幕内容 
    优先级：1. 同目录下与视频同名的字幕文件 2. 字幕目录下与视频同名的字幕文件 3. 默认字幕
    """
    video_name = os.path.splitext(os.path.basename(video_file))[0]

    # 3. 返回默认字幕
    return "我是宝宝我还不会说话但是我和你们说，我是宝宝我还不会说话但是我和你们说，我是宝宝我还不会说话但是我和你们说"

# ---------------------- 获取视频文件并排序 ----------------------
# 获取视频目录下的所有视频文件（按文件名排序）
video_files = []
for file in os.listdir(video_path):
    file_ext = os.path.splitext(file)[1].lower()
    if file_ext in SUPPORTED_VIDEO_FORMATS:
        video_files.append(os.path.join(video_path, file))

# 按文件名排序（确保拼接顺序可预期）
video_files.sort()
video_files = video_files[:5]
# 检查是否有视频文件
if not video_files:
    raise ValueError(f"在目录 {video_path} 中未找到任何支持的视频文件")

# ---------------------- 创建剪映草稿 ----------------------
script = draft_folder.create_draft("多视频拼接+对应字幕2", 1080, 1920, allow_replace=True)

# 添加音频、视频和文本轨道（文本轨道可以多个，这里共用一个）
script.add_track(draft.TrackType.audio).add_track(draft.TrackType.video).add_track(draft.TrackType.text)

# ---------------------- 音频部分（保持原有设置）----------------------
audio_segment = draft.AudioSegment(os.path.join(tutorial_asset_dir, 'audio.mp3'),
                                   trange("0s", "5s"),  # 音频时长5s，可根据需要调整
                                   volume=0.6)
audio_segment.add_fade("1s", "0s")
script.add_segment(audio_segment)

# ---------------------- 多视频拼接 + 对应字幕 ----------------------
previous_segment = None  # 用于记录上一个视频片段，方便添加转场
current_start_time = tim("0s")  # 当前视频片段的开始时间

for i, video_file in enumerate(video_files):
    # 获取视频素材信息
    video_material = draft.VideoMaterial(video_file)
    video_duration = video_material.duration  # 视频实际时长
    segment_duration = video_duration  # 后续视频使用完整时长
    
    # 视频片段时间范围
    timerange = trange(current_start_time, segment_duration)
    
    # 创建视频片段
    video_segment = draft.VideoSegment(video_file, timerange)
    
    # 第一个视频添加入场动画
    if i == 0:
        video_segment.add_animation(IntroType.斜切)
    
    # 添加视频片段到轨道
    script.add_segment(video_segment)
    
    # ---------------------- 为当前视频添加对应字幕 ----------------------
    # 获取字幕内容
    subtitle_text = get_video_subtitle(video_file, subtitle_path)
    
    # 创建字幕片段（每个视频对应一个独立的文本片段）
    text_segment = draft.TextSegment(
        subtitle_text,
        timerange,  # 字幕时长与当前视频完全一致
        font=draft.FontType.抖音美好体,
        style=draft.TextStyle(
            color=(1,0.74901962280273438,0.090196080505847931),  # 黄色
            size=15,
            align=1,
            auto_wrapping=True
        ),
        clip_settings=draft.ClipSettings(
            transform_y=-0.73,  # 位置在屏幕下方
        )
    )
    
    # 为字幕添加入场和出场动画
    # text_segment.add_effect("7296357486490144036")  # 花字效果
    
    # 添加字幕片段到文本轨道
    script.add_segment(text_segment)
    
    # 更新变量，为下一个视频做准备
    previous_segment = video_segment
    current_start_time = timerange.end

# 保存草稿
script.save()

# 打印结果
print(f"成功创建多视频拼接+对应字幕草稿！")
print(f"拼接的视频文件及对应字幕：")
for i, file in enumerate(video_files, 1):
    subtitle = get_video_subtitle(file, subtitle_path)
    print(f"  {i}. 视频：{os.path.basename(file)} -> 字幕：{subtitle}")
print(f"总视频数：{len(video_files)}")
print(f"草稿保存路径：{draft_folder.folder_path}")