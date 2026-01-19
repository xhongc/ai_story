# 完全移除 ProjectStage 的 input_data/output_data 依赖

## 概述

已完成对代码的重构,现在所有数据都从领域模型(ContentRewrite、Storyboard、GeneratedImage、CameraMovement)中读取和写入,`ProjectStage` 的 `input_data` 和 `output_data` 字段不再使用,确保数据的单一来源和一致性。

## 核心原则

### 优化前的问题

```
❌ 数据冗余和不一致
ProjectStage.input_data = {...}   // 数据源1
ProjectStage.output_data = {...}  // 数据源2
ContentRewrite.rewritten_text     // 数据源3
Storyboard.narration_text         // 数据源4
```

**问题**:
- 同一份数据存储在多个地方
- 数据可能不同步
- 难以维护和追踪

### 优化后的方案

```
✅ 单一数据源
Project.original_topic            // 原始输入
    ↓
ContentRewrite.rewritten_text     // 文案改写结果
    ↓
Storyboard.narration_text         // 分镜数据
    ↓
GeneratedImage.image_url          // 生成的图片
CameraMovement.movement_params    // 运镜参数
```

**优势**:
- 每份数据只存储一次
- 数据一致性有保证
- 易于维护和追踪

## 改动内容

### 1. 后端 - LLMStageProcessor

**文件**: `backend/apps/content/processors/llm_stage.py`

#### 改动 1: `process_stream()` 方法

**优化前**:
```python
# 从 ProjectStage.input_data 读取
stage_input_data = stage.input_data
human_text = stage_input_data.get("human_text", "")
```

**优化后**:
```python
# 从领域模型读取
input_data = self._get_input_data(project, stage)
tasks = self._build_tasks(project, input_data)
```

#### 改动 2: 新增 `_build_tasks()` 方法

```python
def _build_tasks(self, project, input_data):
    """根据阶段类型构建任务列表"""
    if self.stage_type == 'camera_movement':
        # 从 Storyboard 模型读取分镜
        storyboards = Storyboard.objects.filter(project=project)
        tasks = []
        for sb in storyboards:
            tasks.append({
                "user_prompt": f'剧本:{sb.narration_text}\n 画面: {sb.image_prompt}',
                "scene_number": sb.sequence_number
            })
        return tasks
```

#### 改动 3: `_save_result()` 方法

**优化前**:
```python
def _save_result(...) -> Dict[str, Any]:
    # 保存到领域模型
    ContentRewrite.objects.update_or_create(...)

    # 返回 output_data
    return {
        'status': 'completed',
        'text_length': len(generated_text)
    }
```

**优化后**:
```python
def _save_result(...) -> None:
    # 只保存到领域模型,不返回 output_data
    ContentRewrite.objects.update_or_create(...)
    # 不再返回任何数据
```

#### 改动 4: 新增 `_get_current_provider()` 方法

```python
def _get_current_provider(self, project):
    """获取当前阶段使用的模型提供商"""
    # 1. 从项目模型配置获取
    # 2. 从提示词模板获取
    # 3. 获取系统默认提供商
    return provider
```

**解决了 Code Review 中发现的问题**: AI客户端没有 `provider` 属性

### 2. 后端 - Text2ImageStageProcessor

**文件**: `backend/apps/content/processors/text2image_stage.py`

#### 改动: `process_stream()` 方法

**优化前**:
```python
# 从 ProjectStage.output_data 读取分镜
storyboards = stage.output_data.get("human_text", {}).get("scenes", [])
```

**优化后**:
```python
# 从 Storyboard 模型读取
storyboards = Storyboard.objects.filter(project=project).order_by('sequence_number')
```

### 3. 后端 - ProjectCreateSerializer

**文件**: `backend/apps/projects/serializers.py`

#### 改动: `create()` 方法

**优化前**:
```python
ProjectStage.objects.create(
    project=project,
    stage_type=stage_type,
    status='pending',
    input_data={"raw_text": project.original_topic, "human_text": ""},
    output_data={"raw_text": "", "human_text": ""}
)
```

**优化后**:
```python
ProjectStage.objects.create(
    project=project,
    stage_type=stage_type,
    status='pending'
    # 不再初始化 input_data 和 output_data
)
```

### 4. 后端 - ProjectStageSerializer

**文件**: `backend/apps/projects/serializers.py`

**保持不变**: 已经添加了 `domain_data` 字段,从领域模型读取数据

```python
def get_domain_data(self, instance):
    """从领域模型读取数据"""
    if stage_type == 'rewrite':
        rewrite = ContentRewrite.objects.get(project=project)
        return {...}
    elif stage_type == 'storyboard':
        storyboards = Storyboard.objects.filter(project=project)
        return {...}
```

## 数据流转

### 文案改写阶段 (rewrite)

```
输入: Project.original_topic
  ↓
处理: LLMStageProcessor.process_stream()
  ↓
输出: ContentRewrite.rewritten_text
  ↓
API: ProjectStageSerializer.domain_data
```

### 分镜生成阶段 (storyboard)

```
输入: ContentRewrite.rewritten_text
  ↓
处理: LLMStageProcessor.process_stream()
  ↓
输出: Storyboard (多条记录)
  ↓
API: ProjectStageSerializer.domain_data
```

### 文生图阶段 (image_generation)

```
输入: Storyboard.image_prompt
  ↓
处理: Text2ImageStageProcessor.process_stream()
  ↓
输出: GeneratedImage (多条记录)
  ↓
API: ProjectStageSerializer.domain_data
```

### 运镜生成阶段 (camera_movement)

```
输入: Storyboard (narration_text + image_prompt)
  ↓
处理: LLMStageProcessor.process_stream()
  ↓
输出: CameraMovement (多条记录)
  ↓
API: ProjectStageSerializer.domain_data
```

## ProjectStage 的新角色

优化后,`ProjectStage` 只负责:

### 1. 阶段状态追踪

```python
{
    "id": "uuid",
    "stage_type": "rewrite",
    "status": "completed",           // ✅ 保留
    "started_at": "2024-01-01...",   // ✅ 保留
    "completed_at": "2024-01-01...", // ✅ 保留
    "retry_count": 0,                // ✅ 保留
    "error_message": "",             // ✅ 保留
    "input_data": {},                // ⚠️ 不再使用
    "output_data": {}                // ⚠️ 不再使用
}
```

### 2. 通过 domain_data 返回真实数据

```python
{
    "id": "uuid",
    "stage_type": "rewrite",
    "status": "completed",
    "domain_data": {                 // ✅ 从领域模型读取
        "id": "uuid",
        "original_text": "...",
        "rewritten_text": "...",
        "model_provider": {...}
    }
}
```

## 向后兼容性

### input_data 和 output_data 字段

- ✅ **字段保留**: 数据库字段仍然存在
- ✅ **API 保留**: 序列化器仍然返回这些字段
- ⚠️ **不再写入**: 新数据不再写入这些字段
- ⚠️ **不再读取**: 处理器不再从这些字段读取

### 迁移策略

如果有旧数据需要迁移:

```python
# 迁移脚本示例
def migrate_old_data(project_id):
    project = Project.objects.get(id=project_id)

    # 1. 迁移文案改写数据
    rewrite_stage = ProjectStage.objects.filter(
        project=project,
        stage_type='rewrite'
    ).first()

    if rewrite_stage and rewrite_stage.output_data:
        ContentRewrite.objects.get_or_create(
            project=project,
            defaults={
                'original_text': project.original_topic,
                'rewritten_text': rewrite_stage.output_data.get('raw_text', ''),
            }
        )

    # 2. 迁移分镜数据
    # ... 类似逻辑
```

## 优势总结

### 1. 数据一致性

✅ **单一数据源**: 每份数据只存储一次
✅ **无冗余**: 不会出现数据不同步的问题
✅ **易于追踪**: 清晰的数据流转路径

### 2. 代码质量

✅ **遵循 DDD**: 领域模型负责业务数据
✅ **职责清晰**: ProjectStage 只负责状态追踪
✅ **易于维护**: 数据逻辑集中在领域模型

### 3. 性能优化

✅ **减少存储**: 不再重复存储相同数据
✅ **查询优化**: 使用 `select_related()` 优化查询
✅ **索引支持**: 领域模型可以添加索引

### 4. 扩展性

✅ **易于扩展**: 添加新字段只需修改领域模型
✅ **易于查询**: 可以使用 Django ORM 的全部功能
✅ **易于统计**: 可以直接对领域模型进行聚合查询

## 测试建议

### 1. 单元测试

```python
def test_rewrite_stage_saves_to_content_rewrite():
    """测试文案改写阶段保存到 ContentRewrite 模型"""
    project = Project.objects.create(...)
    processor = LLMStageProcessor('rewrite')

    # 执行处理
    for chunk in processor.process_stream(project.id):
        pass

    # 验证数据保存到 ContentRewrite
    rewrite = ContentRewrite.objects.get(project=project)
    assert rewrite.rewritten_text != ''
    assert rewrite.model_provider is not None
```

### 2. 集成测试

```python
def test_full_workflow():
    """测试完整的工作流"""
    project = Project.objects.create(original_topic='测试主题')

    # 1. 文案改写
    rewrite_processor = LLMStageProcessor('rewrite')
    for chunk in rewrite_processor.process_stream(project.id):
        pass

    # 验证 ContentRewrite
    rewrite = ContentRewrite.objects.get(project=project)
    assert rewrite.rewritten_text != ''

    # 2. 分镜生成
    storyboard_processor = LLMStageProcessor('storyboard')
    for chunk in storyboard_processor.process_stream(project.id):
        pass

    # 验证 Storyboard
    storyboards = Storyboard.objects.filter(project=project)
    assert storyboards.count() > 0

    # 3. 文生图
    image_processor = Text2ImageStageProcessor()
    for chunk in image_processor.process_stream(project.id):
        pass

    # 验证 GeneratedImage
    images = GeneratedImage.objects.filter(storyboard__project=project)
    assert images.count() > 0
```

### 3. API 测试

```python
def test_api_returns_domain_data():
    """测试 API 返回 domain_data"""
    project = create_test_project_with_data()

    response = client.get(f'/api/v1/projects/{project.id}/')
    data = response.json()

    # 验证 domain_data 存在
    rewrite_stage = next(s for s in data['stages'] if s['stage_type'] == 'rewrite')
    assert rewrite_stage['domain_data'] is not None
    assert 'rewritten_text' in rewrite_stage['domain_data']
    assert 'model_provider' in rewrite_stage['domain_data']
```

## 相关文件

### 后端
- `backend/apps/content/processors/llm_stage.py` ✏️ 重构
- `backend/apps/content/processors/text2image_stage.py` ✏️ 重构
- `backend/apps/projects/serializers.py` ✏️ 修改
- `backend/apps/content/models.py` ✅ 已优化

### 前端
- `frontend/src/components/projects/DomainDataViewer.vue` ✅ 已创建
- `frontend/src/components/projects/StageContent.vue` ✅ 已修改

### 文档
- `backend/REFACTOR_FLOW_DATA_STORAGE.md` - 重构说明
- `backend/CODE_REVIEW_REPORT.md` - 代码审查报告
- `backend/API_STAGE_RESPONSE_FORMAT.md` - API 响应格式
- `backend/REMOVE_INPUT_OUTPUT_DATA_DEPENDENCY.md` - 本文档

## 总结

✅ **已完成**:
- 移除对 `ProjectStage.input_data` 的读取依赖
- 移除对 `ProjectStage.output_data` 的写入依赖
- 所有数据从领域模型读取和写入
- 修复了 Code Review 中发现的 provider 属性问题
- 优化了代码结构和性能

🎯 **核心改进**:
- **数据一致性**: 单一数据源,无冗余
- **代码质量**: 遵循 DDD,职责清晰
- **性能优化**: 减少存储,优化查询
- **易于维护**: 数据逻辑集中,易于扩展

📝 **注意事项**:
- `input_data` 和 `output_data` 字段仍然保留(向后兼容)
- 旧数据可能需要迁移
- 前端可以继续使用 `domain_data` 字段获取数据

现在系统的数据流转完全基于领域模型,确保了数据的一致性和可维护性! 🎉
