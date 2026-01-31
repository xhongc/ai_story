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

        "storyboard": """
{
    "scenes": [
      {
        "scene_number": 1,
        "narration": "一位身着黑色风衣、头戴鸭舌帽的年轻男子，站在城市高楼的天台上，背对着镜头，双手插兜。",
        "visual_prompt": "场景描述:城市高楼的天台边缘，地面铺着灰色防滑地砖，地砖上有一些水渍，远处是灯火辉煌的城市夜景，霓虹灯闪烁着五彩斑斓的光，照亮了城市的轮廓，楼与楼之间的街道上车水马龙，车辆的灯光形成一条条流动的光带，微风从左侧吹过，吹动着男子的衣角。
主体刻画:年轻男子身着黑色长风衣，风衣的拉链拉至脖颈处，头戴黑色鸭舌帽，帽檐微微压低，双手插在风衣口袋里，衣服上的褶皱自然流畅。
风格落地:3D皮克斯风格
光影与质感:月光洒在男子身上，勾勒出他的轮廓，城市的灯光从下方照亮他的脸庞，形成强烈的明暗对比，男子的面部皮肤在光影下显得有质感，黑色风衣反射出微弱的光泽。
视角与构图:远景视角，男子站在画面中央偏后位置，占画面较小比例，突出城市的宏大与男子的渺小，同时通过男子的背影引导观众的视线看向远方的城市。
光线描述:月光从画面右上方斜射下来，城市的灯光从下方多角度照射，月光和城市灯光相互交织，营造出神秘而冷酷的氛围。",
        "shot_type": "远景"
      },
      {
        "scene_number": 2,
        "narration": "男子坐在一间录音棚里，戴着耳机，专注地看着面前的电脑屏幕，手指在键盘上快速地敲击着。",
        "visual_prompt": "场景描述:录音棚内，地面是浅灰色吸音地毯，录音棚的一侧是白色墙壁，墙上挂着一些音乐海报和照片，另一侧是玻璃隔音墙，能看到外面的黑暗。录音棚中央摆放着一张黑色电脑桌，桌上有一台银色电脑，电脑屏幕散发着蓝色光芒，旁边放着一个黑色麦克风，麦克风架上有一些磨损的痕迹。
主体刻画:男子坐在黑色电脑椅上，身体微微前倾，戴着黑色耳机，耳机上有一些使用过的划痕，专注地看着电脑屏幕，手指在键盘上快速敲击，浅黄色连体衣上的“小方圆”三个字在电脑屏幕的光线下清晰可见。
风格落地:3D皮克斯风格
光影与质感:柔和的白色灯光从天花板上均匀照射下来，照亮了整个录音棚，男子的脸庞在灯光下显得专注而认真，电脑屏幕的蓝光映在男子的脸上，形成淡淡的光晕。
视角与构图:中景视角，男子占据画面的主要部分，身后的墙壁和设备作为背景，突出男子在录音棚中的专注状态。
光线描述:白色灯光从画面上方垂直照射，电脑屏幕的蓝光作为辅助光，营造出简洁、专业的氛围。",
        "shot_type": "中景"
      },
      {
        "scene_number": 3,
        "narration": "男子站在一个巨大的舞台上，身后是无数的灯光和特效。他手持麦克风，对着台下的观众大声歌唱。",
        "visual_prompt": "场景描述:巨大的舞台上，地面铺着黑色防滑地板，舞台前方有一排彩色灯光，灯光不断闪烁着红、黄、蓝等颜色，舞台后方是一个巨大的LED屏幕，屏幕上播放着各种特效画面，如火焰、星空等。舞台两侧有一些音箱设备，音箱上有一些灰尘。台下是一片人山人海，观众们挥舞着手中的荧光棒，荧光棒的颜色五彩斑斓，形成一片光的海洋。
主体刻画:男子站在舞台中央，手持黑色麦克风，麦克风上有一些汗水的痕迹，对着台下的观众大声歌唱，他的身体随着音乐的节奏不断摇摆，浅黄色连体衣在舞台灯光的照射下显得格外醒目，衣服上的“小方圆”三个字闪闪发光。
风格落地:3D皮克斯风格
光影与质感:强烈的舞台灯光从多个角度照射在男子身上，使他成为舞台上的焦点，舞台上的特效不断闪烁，照亮了整个舞台和观众席，男子的面部皮肤在灯光下显得有光泽，汗水在灯光下反射出晶莹的光芒。
视角与构图:全景视角，整个舞台和台下的观众都在画面中，男子站在画面中央，通过舞台灯光和特效突出男子的主体地位，同时展现出演唱会的热烈氛围。
光线描述:舞台灯光从画面上方、两侧和前方多角度照射，特效灯光在舞台后方闪烁，荧光棒的光在台下形成一片光的海洋，各种光线相互交织，营造出热烈、激情的氛围。",
        "shot_type": "全景"
      },
      {
        "scene_number": 4,
        "narration": "一群穿着普通、表情迷茫的年轻人，挤在一个狭小的房间里，看着电视上播放的男子的演唱会。",
        "visual_prompt": "场景描述:狭小的房间内，地面上堆满了垃圾和杂物，墙壁是灰色的，有些地方的墙皮已经脱落。房间里摆放着一张破旧的沙发，沙发上坐着几个年轻人，沙发旁边有一个小茶几，茶几上放着一些空饮料瓶和零食袋。电视放在房间的一角，电视屏幕上播放着男子在舞台上的精彩表演，电视周围的墙壁上有一些污渍。
主体刻画:几个年轻人穿着普通的衣服，表情迷茫，挤在沙发上看着电视，其中一个年轻人手里拿着一个遥控器，遥控器上的按键有些磨损。浅黄色连体衣的宝宝坐在沙发旁边的地上，好奇地看着电视屏幕，衣服上的“小方圆”三个字被地上的杂物遮挡了一部分。
风格落地:3D皮克斯风格
光影与质感:昏暗的灯光从天花板上照射下来，照亮了房间的一角，电视屏幕的光线闪烁着，映照着年轻人的脸庞，年轻人的面部皮肤在昏暗的灯光下显得有些苍白，衣服上有一些褶皱和污渍。
视角与构图:中景视角，沙发和年轻人占据画面的主要部分，电视在画面的一角，通过电视屏幕上的画面与房间内的环境形成对比，突出年轻人的状态。
光线描述:昏暗的灯光从画面上方垂直照射，电视屏幕的光线作为主要光源，营造出压抑、沉闷的氛围。",
        "shot_type": "中景"
      },
      {
        "scene_number": 5,
        "narration": "男子站在一个空旷的广场上，周围是一群拿着麦克风和摄像机的记者。记者们纷纷向男子提问，质疑他的音乐和人品。",
        "visual_prompt": "场景描述:空旷的广场上，地面是白色大理石地砖，地砖上有一些灰尘和水渍。广场周围是一些高楼大厦和树木，树木的叶子在微风中轻轻摇曳。一群记者拿着麦克风和摄像机围在男子周围，记者们的表情严肃，麦克风和摄像机上有一些品牌标志。
主体刻画:男子站在广场中央，面无表情地看着记者们，他的眼神坚定而自信。他穿着浅黄色连体衣，衣服上的“小方圆”三个字清晰可见，双手自然地垂在身体两侧。
风格落地:3D皮克斯风格
光影与质感:强烈的阳光从上方照射下来，照亮了整个广场和男子的身体，男子的面部皮肤在阳光下显得健康而有光泽，记者们的闪光灯从不同角度照射过来，形成了一道道光影，光影在男子的脸上和身上闪烁。
视角与构图:全景视角，整个广场和记者们都在画面中，男子站在画面中央，通过记者们的包围突出男子的主体地位，同时展现出广场的空旷和严肃的氛围。
光线描述:阳光从画面上方垂直照射，记者们的闪光灯从多个角度照射，阳光和闪光灯相互交织，营造出明亮、严肃的氛围。",
        "shot_type": "全景"
      },
      {
        "scene_number": 6,
        "narration": "男子独自走在一条安静的街道上，街道两旁是一些古老的建筑和树木。他的手中拿着一张CD，上面写着他的名字和专辑名称。",
        "visual_prompt": "场景描述:安静的街道上，地面是青灰色石板路，石板路有些地方有一些青苔。街道两旁是一些古老的建筑，建筑的墙壁是灰色的，有些地方的墙皮已经脱落，窗户上有一些灰尘。建筑之间种着一些树木，树木的叶子在微风中轻轻飘落。
主体刻画:男子独自走在街道中央，手中拿着一张CD，CD的封面上写着他的名字和专辑名称，他的脸上露出满足的笑容。他穿着浅黄色连体衣，衣服上的“小方圆”三个字在阳光的照射下显得格外醒目，衣服的衣角在微风中轻轻摆动。
风格落地:3D皮克斯风格
光影与质感:柔和的阳光透过树木的枝叶洒在男子身上，形成了一道道金色的光斑，光斑在男子的身上和地面上移动。古老的建筑和树木在阳光的照射下显得有层次感，建筑的墙壁和窗户上的光影变化丰富。
视角与构图:中景视角，男子走在画面中央，街道两旁的建筑和树木作为背景，通过阳光和光斑突出男子的主体地位，同时展现出街道的宁静和悠远。
光线描述:阳光从画面上方斜射下来，透过树木的枝叶形成光斑，微风轻轻吹动树叶，光斑在男子身上和地面上移动，营造出宁静、悠远的氛围。",
        "shot_type": "中景"
      }
    ]
  }
""",

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
        response_text = self._get_mock_response(system_prompt)

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
            return self.MOCK_RESPONSES['storyboard']

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
