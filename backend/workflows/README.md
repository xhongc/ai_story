# ComfyUI Workflow 文件

本目录存放 ComfyUI 工作流 JSON 文件。

## 获取 Workflow 文件

1. **方法一：从 ComfyUI 导出**
   - 在 ComfyUI 界面中设计好工作流
   - 点击 "Save" 或导出为 JSON
   - 将文件放入本目录

2. **方法二：从 GitHub 克隆**
   ```bash
   # 如果你有访问权限
   git clone https://github.com/niuniulin-hue/comfyui_z_image.git
   # 复制 workflows 目录下的 JSON 文件到本目录
   ```

3. **方法三：使用默认模板**
   - `z_image_t2i_lora_style.json` - 动漫风格文生图工作流（需要从 ComfyUI 界面导出）

## 文件说明

| 文件 | 说明 |
|------|------|
| `z_image_t2i_lora_style.json` | LoRA 风格化文生图工作流 |

## 配置说明

工作流中需要动态替换的节点：
- `CLIP Text Encode (Prompt)` - 提示词输入
- `KSampler` - 采样器参数
- `Save Image` / `Preview` - 输出节点

请确保工作流中的节点 ID 与 ComfyUI 服务器上的配置一致。
