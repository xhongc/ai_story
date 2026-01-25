import json
import re


def _extract_json_from_text(text: str) -> str:
        """从文本中提取JSON内容,处理可能包含markdown代码块的情况"""
        # 尝试移除 markdown 代码块标记
        text = text.strip()

        # 如果有 ```json 或 ``` 标记,提取其中的内容
        if '```' in text:
            # 匹配 ```json ... ``` 或 ``` ... ```
            match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        return text.replace("\n", "")

def parse_storyboard_json(json_text: str) -> dict:
    """解析分镜JSON数据"""
    try:
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)

        # 解析JSON
        storyboard_data = json.loads(clean_json)

        # 验证数据结构
        if 'scenes' not in storyboard_data:
            raise ValueError("JSON数据中缺少 'scenes' 字段")

        if not isinstance(storyboard_data['scenes'], list):
            raise ValueError("'scenes' 必须是数组类型")

        # 验证每个场景的必需字段
        for i, scene in enumerate(storyboard_data['scenes']):
            required_fields = ['scene_number', 'narration', 'visual_prompt', 'shot_type']
            for field in required_fields:
                if field not in scene:
                    raise ValueError(f"场景 {i+1} 缺少必需字段: {field}")

        return storyboard_data

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {str(e)}\n原始内容:\n{json_text[:200]}...")
    except Exception as e:
        raise ValueError(f"分镜数据解析失败: {str(e)}")


def parse_json(json_text: str) -> dict:
    """解析JSON数据"""
    try:
        # 提取纯JSON内容
        clean_json = _extract_json_from_text(json_text)

        # 解析JSON
        data = json.loads(clean_json)

        return data

    except json.JSONDecodeError:
        return ""
    except Exception:
        return ""