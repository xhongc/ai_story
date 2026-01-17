# Mock API 使用说明

## 概述

Mock API 是为 AI Story 生成系统开发的模拟 API 系统，用于在开发和测试环境中快速验证工作流，无需调用真实的 AI 服务。

## 功能特性

### 1. Mock LLM 客户端
- **用途**: 文案改写、分镜生成、运镜生成
- **特点**:
  - 返回预定义的模拟响应
  - 支持流式和非流式生成
  - 根据提示词关键词智能返回不同类型的响应
  - 模拟真实的延迟和 token 使用量

### 2. Mock 文生图客户端
- **用途**: 图片生成测试
- **特点**:
  - 返回占位图片 URL（使用 picsum.photos 服务）
  - 支持多张图片生成
  - 相同提示词返回相同图片（可复现）
  - 模拟真实的生成延迟

### 3. Mock 图生视频客户端
- **用途**: 视频生成测试
- **特点**:
  - 返回示例视频 URL
  - 支持运镜参数
  - 模拟真实的视频生成延迟

## 安装配置

### 1. 运行数据库迁移

Mock API 的配置已通过数据库迁移自动创建：

```bash
cd backend
uv run python manage.py migrate
```

迁移会自动创建：
- 3 个 Mock API 模型提供商（LLM、文生图、图生视频）
- 1 个 Mock API 提示词模板集（包含 5 个阶段的模板）

### 2. 验证安装

运行测试脚本验证 Mock API 是否正常工作：

```bash
cd backend
uv run python test_mock_api.py
```

如果所有测试通过，说明 Mock API 已成功配置。

## 使用方法

### 方式一：在 Django Admin 中配置

1. **访问 Django Admin**: http://localhost:8000/admin

2. **查看模型提供商**:
   - 导航到 "模型管理" → "模型提供商"
   - 可以看到三个 Mock API 提供商：
     - Mock LLM API
     - Mock Text2Image API
     - Mock Image2Video API

3. **查看提示词模板集**:
   - 导航到 "提示词管理" → "提示词集"
   - 可以看到 "Mock API 测试模板集"
   - 包含 5 个阶段的提示词模板

4. **创建测试项目**:
   - 导航到 "项目管理" → "项目"
   - 创建新项目
   - 选择 "Mock API 测试模板集" 作为提示词集
   - 在项目模型配置中选择 Mock API 提供商

### 方式二：通过 API 使用

#### 创建项目并配置 Mock API

```python
import requests

# 创建项目
response = requests.post('http://localhost:8000/api/v1/projects/', json={
    'name': 'Mock API 测试项目',
    'description': '使用 Mock API 进行测试',
    'original_content': '一个年轻人在城市中寻找梦想的故事',
    'prompt_template_set': '<Mock API 测试模板集的 UUID>',
})

project_id = response.json()['id']

# 配置项目使用 Mock API
requests.post(f'http://localhost:8000/api/v1/projects/{project_id}/configure_models/', json={
    'rewrite': ['<Mock LLM API 的 UUID>'],
    'storyboard': ['<Mock LLM API 的 UUID>'],
    'image_generation': ['<Mock Text2Image API 的 UUID>'],
    'camera_movement': ['<Mock LLM API 的 UUID>'],
    'video_generation': ['<Mock Image2Video API 的 UUID>'],
})

# 启动工作流
requests.post(f'http://localhost:8000/api/v1/projects/{project_id}/start_pipeline/')
```

### 方式三：在代码中直接使用

```python
from core.ai_client.mock_llm_client import MockLLMClient
from core.ai_client.mock_text2image_client import MockText2ImageClient
from core.ai_client.mock_image2video_client import MockImage2VideoClient

# 使用 Mock LLM 客户端
llm_client = MockLLMClient(
    api_url="http://localhost:8000/api/mock",
    api_key="mock-key",
    model_name="mock-llm-v1"
)

response = await llm_client.generate(
    prompt="请改写以下内容：...",
    max_tokens=500
)

# 使用 Mock 文生图客户端
image_client = MockText2ImageClient(
    api_url="http://localhost:8000/api/mock",
    api_key="mock-key",
    model_name="mock-text2image-v1"
)

response = image_client.generate(
    prompt="A beautiful sunset",
    width=1024,
    height=1024
)

# 使用 Mock 图生视频客户端
video_client = MockImage2VideoClient(
    api_url="http://localhost:8000/api/mock",
    api_key="mock-key",
    model_name="mock-image2video-v1"
)

response = await video_client.generate(
    image_url="https://example.com/image.jpg",
    camera_movement={"movement_type": "zoom_in"},
    duration=3.0,
    fps=24
)
```

### 方式四：通过 HTTP 接口直接调用

Mock API 也在 Django 服务中提供了真实的 HTTP 端点（默认根地址为 `http://localhost:8000/api/mock/`），用于和其他语言或应用集成：

| Endpoint | Method | 说明 |
| --- | --- | --- |
| `/api/mock/` | `GET` | 查看可用的 Mock 服务以及各端点地址 |
| `/api/mock/llm/` | `POST` | 文案改写/分镜/运镜等文本生成 |
| `/api/mock/text2image/` | `POST` | 文生图模拟输出，返回图片 URL 列表 |
| `/api/mock/image2video/` | `POST` | 图生视频模拟输出，返回示例视频信息 |

示例请求：

```bash
# 调用 LLM Mock 接口
curl -X POST http://localhost:8000/api/mock/llm/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "请改写下面的故事"}'

# 生成占位图片
curl -X POST http://localhost:8000/api/mock/text2image/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset", "sample_count": 2}'

# 生成占位视频
curl -X POST http://localhost:8000/api/mock/image2video/ \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://picsum.photos/1024/1024"}'

# LLM 流式（OpenAI SSE 兼容）
curl -N http://localhost:8000/api/mock/llm/ \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"prompt": "请改写下面的故事", "stream": true}'
```

接口返回格式与 `core/ai_client` 中的 Mock 客户端保持一致，可直接替换真实 API 的调用逻辑。

> ℹ️ `stream=true` 时，`/api/mock/llm/` 会输出 `text/event-stream`，其内容结构和 OpenAI `chat.completions` 的流式返回兼容，可直接用于需要 SSE 的客户端。

## Mock 响应说明

### LLM 响应类型

Mock LLM 客户端会根据提示词中的关键词返回不同类型的响应：

1. **文案改写** (关键词: 改写、rewrite、润色、优化文案)
   - 返回改写后的故事内容

2. **分镜生成** (关键词: 分镜、storyboard、场景、scene)
   - 返回 JSON 格式的分镜数组
   - 包含场景描述、旁白、图片提示词、时长、运镜方式

3. **运镜生成** (关键词: 运镜、camera、镜头、movement)
   - 返回 JSON 格式的运镜参数
   - 包含运镜类型和参数

4. **默认响应**
   - 返回通用的模拟文本

### 文生图响应

- 返回占位图片 URL（使用 https://picsum.photos 服务）
- 相同的提示词会返回相同的图片（基于哈希）
- 支持生成多张图片

### 图生视频响应

- 返回示例视频 URL
- 包含视频元数据（宽度、高度、时长、帧率等）
- 相同的源图片会返回相同的视频

## 性能特性

### 模拟延迟

Mock API 会模拟真实 API 的延迟：

- **LLM 生成**: 500ms
- **文生图**: 1000ms
- **图生视频**: 2000ms
- **流式生成**: 每个 chunk 50ms

### Token 使用量

Mock LLM 客户端会估算 token 使用量：
- 粗略估算：字符数 ÷ 4

## 使用场景

### 1. 开发环境测试
- 快速验证工作流逻辑
- 无需配置真实 API 密钥
- 节省 API 调用成本

### 2. 前端开发
- 前端界面调试
- 实时预览功能
- 测试错误处理

### 3. CI/CD 自动化测试
- 单元测试
- 集成测试
- 端到端测试

### 4. 演示和培训
- 产品演示
- 用户培训
- 功能展示

## 注意事项

### 1. 仅用于测试
Mock API 返回的是预定义的模拟数据，不是真实的 AI 生成内容。**不要在生产环境中使用**。

### 2. 图片和视频 URL
- 图片 URL 使用第三方占位图服务，需要网络连接
- 视频 URL 指向公开的示例视频
- 如果需要离线使用，可以修改客户端返回本地文件路径

### 3. 响应格式
Mock API 的响应格式与真实 API 保持一致，确保代码兼容性。

### 4. 性能
Mock API 的延迟是固定的，不会随负载变化。真实 API 的延迟会受网络、服务器负载等因素影响。

## 自定义 Mock 响应

如果需要自定义 Mock 响应，可以修改客户端代码：

### 修改 LLM 响应

编辑 `backend/core/ai_client/mock_llm_client.py`：

```python
MOCK_RESPONSES = {
    "rewrite": "你的自定义改写响应",
    "storyboard": "你的自定义分镜响应",
    # ...
}
```

### 修改图片 URL

编辑 `backend/core/ai_client/mock_text2image_client.py`：

```python
MOCK_IMAGE_URLS = [
    "https://your-custom-image-url-1.jpg",
    "https://your-custom-image-url-2.jpg",
    # ...
]
```

### 修改视频 URL

编辑 `backend/core/ai_client/mock_image2video_client.py`：

```python
MOCK_VIDEO_URLS = [
    "https://your-custom-video-url-1.mp4",
    "https://your-custom-video-url-2.mp4",
    # ...
]
```

## 故障排查

### 问题：迁移失败

**解决方案**:
```bash
# 检查迁移状态
uv run python manage.py showmigrations

# 重新运行迁移
uv run python manage.py migrate
```

### 问题：测试脚本失败

**解决方案**:
```bash
# 检查 Django 设置
echo $DJANGO_SETTINGS_MODULE

# 确保在 backend 目录下运行
cd backend
uv run python test_mock_api.py
```

### 问题：找不到 Mock API 提供商

**解决方案**:
1. 确认迁移已运行：`uv run python manage.py migrate models`
2. 在 Django Admin 中检查模型提供商列表
3. 如果不存在，手动创建或重新运行迁移

## 文件清单

Mock API 相关的文件：

```
backend/
├── core/ai_client/
│   ├── mock_llm_client.py              # Mock LLM 客户端
│   ├── mock_text2image_client.py       # Mock 文生图客户端
│   └── mock_image2video_client.py      # Mock 图生视频客户端
├── apps/models/migrations/
│   └── 0004_create_mock_providers.py   # Mock 提供商迁移
├── apps/prompts/migrations/
│   └── 0005_create_mock_prompt_templates.py  # Mock 模板迁移
├── test_mock_api.py                    # 测试脚本
└── MOCK_API_GUIDE.md                   # 本文档
```

## 下一步

1. **配置真实 API**: 在生产环境中，配置真实的 LLM、文生图、图生视频 API
2. **切换提供商**: 在项目配置中切换到真实的 API 提供商
3. **监控使用**: 使用模型使用日志监控 API 调用情况
4. **成本优化**: 根据使用情况优化 API 调用策略

## 支持

如有问题或建议，请联系开发团队或提交 Issue。
