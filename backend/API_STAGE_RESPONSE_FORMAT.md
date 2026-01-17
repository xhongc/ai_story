# API 阶段响应格式说明

## 概述

在流程记录格式优化后,`ProjectStageSerializer` 现在会返回真实的领域模型数据,而不仅仅是 `ProjectStage` 的 `input_data` 和 `output_data` JSONField。

## API 端点

```
GET /api/v1/projects/{project_id}/stages/
GET /api/v1/projects/{project_id}/
```

## 响应格式

每个 `ProjectStage` 对象现在包含一个新的 `domain_data` 字段,根据阶段类型返回不同的数据结构。

### 基础字段

所有阶段都包含以下基础字段:

```json
{
  "id": "uuid",
  "project": "uuid",
  "stage_type": "rewrite|storyboard|image_generation|camera_movement|video_generation",
  "stage_type_display": "文案改写|分镜生成|文生图|运镜生成|图生视频",
  "status": "pending|processing|completed|failed",
  "status_display": "待处理|处理中|已完成|失败",
  "input_data": {},
  "output_data": {},
  "retry_count": 0,
  "max_retries": 3,
  "error_message": "",
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "domain_data": {}  // 新增字段,根据阶段类型返回不同数据
}
```

---

## 各阶段的 domain_data 格式

### 1. 文案改写阶段 (rewrite)

返回 `ContentRewrite` 模型数据:

```json
{
  "stage_type": "rewrite",
  "domain_data": {
    "id": "uuid",
    "original_text": "原始文本内容",
    "rewritten_text": "改写后的文本内容",
    "model_provider": {
      "id": "uuid",
      "name": "OpenAI GPT-4",
      "model_name": "gpt-4-turbo"
    },
    "prompt_used": "使用的提示词内容",
    "generation_metadata": {
      "tokens_used": 1234,
      "temperature": 0.7
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**字段说明:**
- `original_text`: 原始输入文本
- `rewritten_text`: AI 改写后的文本
- `model_provider`: 使用的模型提供商信息
- `prompt_used`: 实际使用的提示词
- `generation_metadata`: 生成过程的元数据

---

### 2. 分镜生成阶段 (storyboard)

返回 `Storyboard` 模型列表:

```json
{
  "stage_type": "storyboard",
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "id": "uuid",
        "sequence_number": 1,
        "scene_description": "特写镜头",
        "narration_text": "旁白文案内容",
        "image_prompt": "文生图提示词",
        "duration_seconds": 3.0,
        "model_provider": {
          "id": "uuid",
          "name": "OpenAI GPT-4",
          "model_name": "gpt-4-turbo"
        },
        "prompt_used": "使用的提示词",
        "generation_metadata": {
          "shot_type": "close_up",
          "raw_scene_data": {}
        },
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      },
      // ... 更多分镜
    ]
  }
}
```

**字段说明:**
- `count`: 分镜总数
- `storyboards`: 分镜列表,按 `sequence_number` 排序
- `sequence_number`: 分镜序号
- `scene_description`: 场景描述(镜头类型)
- `narration_text`: 旁白文案
- `image_prompt`: 用于生成图片的提示词
- `duration_seconds`: 分镜时长(秒)

---

### 3. 文生图阶段 (image_generation)

返回每个分镜生成的图片列表:

```json
{
  "stage_type": "image_generation",
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "storyboard_id": "uuid",
        "sequence_number": 1,
        "images": [
          {
            "id": "uuid",
            "image_url": "https://example.com/image.jpg",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "width": 1920,
            "height": 1080,
            "file_size": 1024000,
            "status": "completed",
            "status_display": "已完成",
            "model_provider": {
              "id": "uuid",
              "name": "Stable Diffusion",
              "model_name": "sd-xl-1.0"
            },
            "generation_params": {
              "prompt": "文生图提示词",
              "model": "sd-xl-1.0",
              "original_data": {}
            },
            "retry_count": 0,
            "created_at": "2024-01-01T00:00:00Z"
          }
          // 可能有多张图片(重试或多次生成)
        ]
      },
      // ... 更多分镜的图片
    ]
  }
}
```

**字段说明:**
- `count`: 有图片的分镜数量
- `storyboards`: ���分镜组织的图片列表
- `images`: 每个分镜生成的图片列表(按创建时间倒序)
- `status`: 图片生成状态 (pending/processing/completed/failed)
- `generation_params`: 生成参数,包含提示词和模型信息

---

### 4. 运镜生成阶段 (camera_movement)

返回每个分镜的运镜参数:

```json
{
  "stage_type": "camera_movement",
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "storyboard_id": "uuid",
        "sequence_number": 1,
        "camera_movement": {
          "id": "uuid",
          "movement_type": "zoom_in",
          "movement_type_display": "推进",
          "movement_params": {
            "speed": "slow",
            "duration": 3.0,
            "raw_text": "原始运镜描述"
          },
          "model_provider": {
            "id": "uuid",
            "name": "OpenAI GPT-4",
            "model_name": "gpt-4-turbo"
          },
          "prompt_used": "使用的提示词",
          "generation_metadata": {
            "index": 1
          },
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:00:00Z"
        }
      },
      // 如果某个分镜没有运镜数据
      {
        "storyboard_id": "uuid",
        "sequence_number": 2,
        "camera_movement": null
      }
    ]
  }
}
```

**字段说明:**
- `count`: 分镜总数
- `storyboards`: 按分镜组织的运镜数据
- `movement_type`: 运镜类型 (static/zoom_in/zoom_out/pan_left/pan_right/tilt_up/tilt_down/dolly_in/dolly_out)
- `movement_params`: 运镜参数,可能包含 `raw_text` (如果解析失败)
- `camera_movement`: 如果分镜没有运镜数据,则为 `null`

---

### 5. 图生视频阶段 (video_generation)

```json
{
  "stage_type": "video_generation",
  "domain_data": null  // TODO: 待实现
}
```

---

## 使用示例

### 获取项目的所有阶段数据

```bash
GET /api/v1/projects/{project_id}/
```

**响应:**

```json
{
  "id": "uuid",
  "name": "项目名称",
  "stages": [
    {
      "id": "uuid",
      "stage_type": "rewrite",
      "status": "completed",
      "domain_data": {
        "id": "uuid",
        "original_text": "...",
        "rewritten_text": "..."
      }
    },
    {
      "id": "uuid",
      "stage_type": "storyboard",
      "status": "completed",
      "domain_data": {
        "count": 5,
        "storyboards": [...]
      }
    },
    {
      "id": "uuid",
      "stage_type": "image_generation",
      "status": "processing",
      "domain_data": {
        "count": 3,
        "storyboards": [...]
      }
    }
  ]
}
```

---

## 性能优化

序列化器使用了以下优化:

1. **select_related**: 预加载 `model_provider` 外键,避免 N+1 查询
2. **order_by**: 确保数据按正确顺序返回
3. **异常处理**: 如果获取领域数据失败,返回 `null` 而不中断整个序列化

---

## 向后兼容性

- `input_data` 和 `output_data` 字段仍然保留
- 旧的前端代码可以继续使用这些字段
- 新的前端代码应该使用 `domain_data` 字段获取结构化数据

---

## 数据为空的情况

如果某个阶段还没有生成数据,`domain_data` 将返回:

- **rewrite**: `null` (如果 `ContentRewrite` 不存在)
- **storyboard**: `{"count": 0, "storyboards": []}`
- **image_generation**: `{"count": 0, "storyboards": []}`
- **camera_movement**: `{"count": N, "storyboards": [{"camera_movement": null}, ...]}`
- **video_generation**: `null`

---

## 前端使用建议

### 检查数据是否存在

```javascript
// 检查文案改写数据
if (stage.domain_data && stage.domain_data.rewritten_text) {
  console.log('改写后的文本:', stage.domain_data.rewritten_text);
}

// 检查分镜数据
if (stage.domain_data && stage.domain_data.count > 0) {
  stage.domain_data.storyboards.forEach(sb => {
    console.log(`分镜 ${sb.sequence_number}:`, sb.narration_text);
  });
}

// 检查图片数据
if (stage.domain_data && stage.domain_data.storyboards) {
  stage.domain_data.storyboards.forEach(sb => {
    if (sb.images.length > 0) {
      console.log(`分镜 ${sb.sequence_number} 的图片:`, sb.images[0].image_url);
    }
  });
}
```

### 显示模型提供商信息

```javascript
// 显示使用的模型
if (stage.domain_data && stage.domain_data.model_provider) {
  console.log('使用的模型:', stage.domain_data.model_provider.name);
}

// 对于分镜列表
if (stage.domain_data && stage.domain_data.storyboards) {
  stage.domain_data.storyboards.forEach(sb => {
    if (sb.model_provider) {
      console.log(`分镜 ${sb.sequence_number} 使用的模型:`, sb.model_provider.name);
    }
  });
}
```

---

## 总结

新的 API 响应格式提供了:

✅ **结构化数据**: 不再需要解析 JSONField
✅ **完整信息**: 包含模型提供商、提示词、元数据等
✅ **类型安全**: 明确的数据结构,易于前端类型定义
✅ **性能优化**: 使用 select_related 避免 N+1 查询
✅ **向后兼容**: 保留旧的 input_data 和 output_data 字段

前端可以根据需要选择使用 `domain_data` (推荐) 或继续使用 `input_data`/`output_data` (兼容旧代码)。
