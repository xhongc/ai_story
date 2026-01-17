# 流程记录格式优化文档

## 优化概述

本次重构将流程数据从 `ProjectStage` 的 `input_data` 和 `output_data` JSONField 迁移到专门的领域模型中,遵循单一职责原则和领域驱动设计。

## 问题分析

### 优化前的问题

1. **数据冗余严重**: 同样的数据在多个 `ProjectStage` 中重复存储
   - 分镜数据同时存在于 `storyboard`、`image_generation`、`camera_movement`、`video_generation` 阶段
   - 图片URL在 `image_generation` 和 `video_generation` 阶段重复存储

2. **违反单一职责原则**: `ProjectStage` 既负责追踪阶段状态,又存储业务数据

3. **数据结构不清晰**: JSONField 中的数据结构难以维护和查询

4. **领域模型未被充分利用**: `apps/content/models.py` 中已定义的模型未被使用

## 优化方案

### 核心思路

- **ProjectStage 只存储阶段元数据**: 状态、时间戳、重试次数、错误信息、简单的统计数据
- **业务数据存储到领域模型**: ContentRewrite、Storyboard、CameraMovement、GeneratedImage、GeneratedVideo
- **通过外键关联建立数据流转**: 清晰的数据依赖关系

### 数据流转设计

```
Project (原始主题)
    ↓
ContentRewrite (文案改写结果)
    ↓
Storyboard (多个分镜)
    ↓
├─→ GeneratedImage (生成的图片)
└─→ CameraMovement (运镜参数)
    ↓
GeneratedVideo (生成的视频)
```

## 模型变更

### 1. ContentRewrite 模型

**新增字段:**
- `updated_at`: 更新时间 (DateTimeField, auto_now=True)

**修改字段:**
- `prompt_used`: 添加 `blank=True, default=''`
- `generation_metadata`: 添加 `blank=True`

### 2. Storyboard 模型

**新增字段:**
- `model_provider`: 使用的模型提供商 (ForeignKey to ModelProvider)
- `prompt_used`: 使用的提示词 (TextField)
- `generation_metadata`: 生成元数据 (JSONField)

### 3. CameraMovement 模型

**新增字段:**
- `generation_metadata`: 生成元数据 (JSONField)
- `updated_at`: 更新时间 (DateTimeField, auto_now=True)

**修改字段:**
- `movement_type`: 添加 `blank=True, default=''`
- `movement_params`: 添加 `blank=True`
- `prompt_used`: 添加 `blank=True, default=''`
- `model_provider`: 添加 `blank=True`

## 处理器变更

### 1. LLMStageProcessor

#### `_save_result()` 方法重构

**文案改写阶段 (rewrite):**
```python
# 优化前: 保存到 ProjectStage.output_data
output_data = {'raw_text': generated_text, 'human_text': ''}
ProjectStage.objects.filter(...).update(input_data=output_data)

# 优化后: 保存到 ContentRewrite 模型
ContentRewrite.objects.update_or_create(
    project=project,
    defaults={
        'original_text': project.original_topic,
        'rewritten_text': generated_text,
        'prompt_used': prompt_used,
        'model_provider': provider,
        'generation_metadata': metadata
    }
)
```

**分镜生成阶段 (storyboard):**
```python
# 优化前: 解析JSON后保存到 ProjectStage.output_data
output_data = {'human_text': parsed_json, 'raw_text': generated_text}
ProjectStage.objects.filter(...).update(input_data=output_data, output_data=output_data)

# 优化后: 保存到 Storyboard 模型
for scene in scenes:
    Storyboard.objects.update_or_create(
        project=project,
        sequence_number=scene['scene_number'],
        defaults={
            'scene_description': scene.get('shot_type', ''),
            'narration_text': scene.get('narration', ''),
            'image_prompt': scene.get('visual_prompt', ''),
            'duration_seconds': scene.get('duration', 3.0),
            'model_provider': provider,
            'prompt_used': prompt_used,
            'generation_metadata': {...}
        }
    )
```

**运镜生成阶段 (camera_movement):**
```python
# 优化前: 保存到 ProjectStage.output_data 的嵌套结构中
scenes = stage.output_data.get("human_text", {}).get("scenes", [])
for each in scenes:
    if each["scene_number"] == index:
        each["camera_movement"] = generated_text

# 优化后: 保存到 CameraMovement 模型
CameraMovement.objects.update_or_create(
    storyboard=storyboard,
    defaults={
        'movement_type': movement_type,
        'movement_params': movement_params,
        'model_provider': provider,
        'prompt_used': prompt_used,
        'generation_metadata': metadata
    }
)
```

#### `_get_input_data()` 方法重构

**优化前:** 从 `ProjectStage.input_data` 或前置阶段的 `output_data` 读取

**优化后:** 从领域模型读取

```python
# 文案改写: 从 Project 读取
return {'raw_text': project.original_topic}

# 分镜生成: 从 ContentRewrite 读取
content_rewrite = ContentRewrite.objects.get(project=project)
return {'raw_text': content_rewrite.rewritten_text}

# 运镜生成: 从 Storyboard 读取
storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')
scenes = [{'scene_number': sb.sequence_number, 'narration': sb.narration_text, ...} for sb in storyboards]
return {'human_text': {'scenes': scenes}}
```

### 2. Text2ImageStageProcessor

#### `_save_result()` 方法重构

**优化前:** 保存到 `ProjectStage.output_data` 和 `video_generation` 阶段的 `input_data`/`output_data`

**优化后:** 保存到 `GeneratedImage` 模型

```python
# 获取对应的 Storyboard 对象
storyboard_obj = Storyboard.objects.filter(
    project=project,
    sequence_number=scene_number
).first()

# 保存每张生成的图片
for image_data in result:
    GeneratedImage.objects.create(
        storyboard=storyboard_obj,
        image_url=image_data.get('url', ''),
        generation_params={...},
        model_provider=provider,
        status='completed',
        width=image_data.get('width', 0),
        height=image_data.get('height', 0)
    )
```

#### `process_stream()` 方法重构

**优化前:** 从 `ProjectStage.output_data` 读取分镜数据

**优化后:** 从 `Storyboard` 模型读取

```python
# 从 Storyboard 模型获取分镜列表
storyboards_query = Storyboard.objects.filter(project=project).order_by('sequence_number')

# 如果指定了分镜ID,则只处理这些分镜
if storyboard_ids:
    storyboards_query = storyboards_query.filter(sequence_number__in=storyboard_ids)

storyboards = list(storyboards_query)
```

## ProjectStage 的新角色

优化后,`ProjectStage` 只存储:

1. **阶段元数据**:
   - `status`: 阶段状态 (pending/processing/completed/failed)
   - `started_at`: 开始时间
   - `completed_at`: 完成时间
   - `retry_count`: 重试次数
   - `error_message`: 错误信息

2. **简单的统计数据** (存储在 `output_data` 中):
   ```python
   # 文案改写
   {'status': 'completed', 'text_length': 1234}

   # 分镜生成
   {'status': 'completed', 'storyboard_count': 5, 'storyboard_ids': [...]}

   # 文生图
   {'total_storyboards': 5, 'success_count': 5, 'failed_count': 0}

   # 运镜生成
   {'status': 'completed', 'storyboard_id': '...', 'scene_number': 1}
   ```

## 数据库迁移

迁移文件: `apps/content/migrations/0002_auto_20260116_1030.py`

**变更内容:**
- 为 `ContentRewrite` 添加 `updated_at` 字段
- 为 `Storyboard` 添加 `model_provider`、`prompt_used`、`generation_metadata` 字段
- 为 `CameraMovement` 添加 `generation_metadata`、`updated_at` 字段
- 修改多个字段的约束,添加 `blank=True` 和默认值

## 优势总结

### 1. 数据结构清晰
- 每个领域模型负责一种业务数据
- 通过外键建立清晰的数据依赖关系
- 易于理解和维护

### 2. 消除数据冗余
- 每份数据只存储一次
- 通过外键关联访问相关数据
- 减少数据不一致的风险

### 3. 遵循设计原则
- **单一职责原则 (SRP)**: 每个模型只负责一种数据
- **开闭原则 (OCP)**: 新增阶段不影响现有模型
- **领域驱动设计 (DDD)**: 模型反映业务领域

### 4. 查询性能优化
- 可以使用 Django ORM 的 `select_related()` 和 `prefetch_related()` 优化查询
- 可以为常用查询字段添加索引
- 避免解析大型 JSONField

### 5. 数据完整性
- 利用数据库外键约束保证数据完整性
- 级联删除自动清理相关数据
- 字段类型约束防止错误数据

## 向后兼容性

### 潜在影响

1. **API 响应格式**: 如果前端依赖 `ProjectStage.output_data` 的结构,需要调整
2. **序列化器**: 可能需要更新 `ProjectStageSerializer` 来包含关联数据
3. **现有数据**: 旧数据仍存储在 `ProjectStage.output_data` 中,新数据存储在领域模型中

### 建议的迁移策略

1. **数据迁移脚本**: 将现有的 `ProjectStage.output_data` 数据迁移到领域模型
2. **API 版本控制**: 提供新旧两个版本的 API,逐步废弃旧版本
3. **渐进式重构**: 先支持新模型,保留旧数据读取逻辑作为 fallback

## 后续优化建议

1. **添加序列化器**: 为领域模型创建专门的序列化器
2. **优化查询**: 使用 `select_related()` 和 `prefetch_related()` 减少数据库查询
3. **添加索引**: 为常用查询字段添加数据库索引
4. **数据迁移**: 编写脚本将旧数据迁移到新模型
5. **API 文档**: 更新 API 文档,说明新的数据结构
6. **单元测试**: 为新的数据流转逻辑编写测试用例

## 相关文件

### 模型文件
- `backend/apps/content/models.py` - 领域模型定义

### 处理器文件
- `backend/apps/content/processors/llm_stage.py` - LLM 阶段处理器
- `backend/apps/content/processors/text2image_stage.py` - 文生图阶段处理器

### 迁移文件
- `backend/apps/content/migrations/0002_auto_20260116_1030.py` - 数据库迁移

## 总结

本次重构通过将业务数据从 `ProjectStage` 的 JSONField 迁移到专门的领域模型,实现了:

✅ 数据结构清晰化
✅ 消除数据冗余
✅ 遵循设计原则
✅ 提升查询性能
✅ 增强数据完整性

这为后续的功能扩展和性能优化奠定了良好的基础。
