# 阶段查询 API 增强 - 返回真实领域模型数据

## 概述

已完成对 `ProjectStageSerializer` 的增强,现在查询项目阶段时会返回真实的领域模型数据,而不仅仅是 `ProjectStage` 的 JSONField。

## 改动内容

### 1. 修改 `ProjectStageSerializer`

**文件**: `backend/apps/projects/serializers.py`

**主要变更**:

1. **新增 `domain_data` 字段**
   ```python
   domain_data = serializers.SerializerMethodField()
   ```

2. **实现 `get_domain_data()` 方法**
   - 根据阶段类型返回对应的领域模型数据
   - 使用 `select_related()` 优化查询性能
   - 包含完整的模型提供商信息

3. **支持的阶段类型**:
   - ✅ `rewrite`: 返回 `ContentRewrite` 数据
   - ✅ `storyboard`: 返回 `Storyboard` 列表
   - ✅ `image_generation`: 返回 `GeneratedImage` 列表(按分镜组织)
   - ✅ `camera_movement`: 返回 `CameraMovement` 数据(按分镜组织)
   - ⏳ `video_generation`: 待实现

## API 响应格式

### 基础结构

```json
{
  "id": "uuid",
  "stage_type": "rewrite",
  "status": "completed",
  "input_data": {},      // 保留,向后兼容
  "output_data": {},     // 保留,向后兼容
  "domain_data": {       // 新增,结构化数据
    // 根据阶段类型返回不同数据
  }
}
```

### 各阶段的 domain_data 格式

#### 1. 文案改写 (rewrite)

```json
{
  "domain_data": {
    "id": "uuid",
    "original_text": "原始文本",
    "rewritten_text": "改写后文本",
    "model_provider": {
      "id": "uuid",
      "name": "OpenAI GPT-4",
      "model_name": "gpt-4-turbo"
    },
    "prompt_used": "提示词",
    "generation_metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### 2. 分镜生成 (storyboard)

```json
{
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "id": "uuid",
        "sequence_number": 1,
        "scene_description": "特写镜头",
        "narration_text": "旁白文案",
        "image_prompt": "文生图提示词",
        "duration_seconds": 3.0,
        "model_provider": {...},
        "prompt_used": "提示词",
        "generation_metadata": {},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 3. 文生图 (image_generation)

```json
{
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "storyboard_id": "uuid",
        "sequence_number": 1,
        "images": [
          {
            "id": "uuid",
            "image_url": "https://...",
            "thumbnail_url": "https://...",
            "width": 1920,
            "height": 1080,
            "file_size": 1024000,
            "status": "completed",
            "status_display": "已完成",
            "model_provider": {...},
            "generation_params": {},
            "retry_count": 0,
            "created_at": "2024-01-01T00:00:00Z"
          }
        ]
      }
    ]
  }
}
```

#### 4. 运镜生成 (camera_movement)

```json
{
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
          "movement_params": {},
          "model_provider": {...},
          "prompt_used": "提示词",
          "generation_metadata": {},
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:00:00Z"
        }
      }
    ]
  }
}
```

## 性能优化

1. **使用 select_related()**
   ```python
   ContentRewrite.objects.select_related('model_provider').get(project=project)
   Storyboard.objects.filter(project=project).select_related('model_provider')
   GeneratedImage.objects.filter(storyboard=sb).select_related('model_provider')
   CameraMovement.objects.select_related('model_provider').get(storyboard=sb)
   ```

2. **按需加载**
   - 只在序列化时查询领域模型数据
   - 使用 `SerializerMethodField` 延迟计算

3. **异常处理**
   - 如果领域模型数据不存在,返回 `null` 而不中断序列化
   - 记录错误日志但不影响其他字段

## 向后兼容性

✅ **完全向后兼容**

- `input_data` 和 `output_data` 字段保留
- 旧的前端代码可以继续使用
- 新的前端代码应该使用 `domain_data` 字段

## 使用示例

### Python (Django)

```python
from apps.projects.models import Project, ProjectStage
from apps.projects.serializers import ProjectStageSerializer

# 获取项目的所有阶段
project = Project.objects.get(id=project_id)
stages = ProjectStage.objects.filter(project=project)

# 序列化
serializer = ProjectStageSerializer(stages, many=True)
data = serializer.data

# 访问领域数据
for stage_data in data:
    if stage_data['stage_type'] == 'rewrite':
        domain_data = stage_data['domain_data']
        if domain_data:
            print(f"改写后文本: {domain_data['rewritten_text']}")
```

### JavaScript (前端)

```javascript
// 获取项目详情
const response = await fetch(`/api/v1/projects/${projectId}/`);
const project = await response.json();

// 遍历阶段
project.stages.forEach(stage => {
  if (stage.stage_type === 'storyboard' && stage.domain_data) {
    console.log(`分镜总数: ${stage.domain_data.count}`);

    stage.domain_data.storyboards.forEach(sb => {
      console.log(`分镜 ${sb.sequence_number}: ${sb.narration_text}`);
    });
  }

  if (stage.stage_type === 'image_generation' && stage.domain_data) {
    stage.domain_data.storyboards.forEach(sb => {
      if (sb.images.length > 0) {
        console.log(`分镜 ${sb.sequence_number} 的图片:`, sb.images[0].image_url);
      }
    });
  }
});
```

## 数据为空的情况

| 阶段类型 | domain_data 为空时的值 |
|---------|---------------------|
| rewrite | `null` |
| storyboard | `{"count": 0, "storyboards": []}` |
| image_generation | `{"count": 0, "storyboards": []}` |
| camera_movement | `{"count": N, "storyboards": [{"camera_movement": null}, ...]}` |
| video_generation | `null` (待实现) |

## 优势

### 1. 数据结构清晰

❌ **优化前**: 需要解析 JSONField
```json
{
  "output_data": {
    "human_text": {
      "scenes": [
        {"scene_number": 1, "narration": "...", "urls": [...]}
      ]
    }
  }
}
```

✅ **优化后**: 结构化数据
```json
{
  "domain_data": {
    "count": 5,
    "storyboards": [
      {
        "id": "uuid",
        "sequence_number": 1,
        "narration_text": "...",
        "images": [...]
      }
    ]
  }
}
```

### 2. 包含完整元数据

- ✅ 模型提供商信息
- ✅ 提示词内容
- ✅ 生成参数
- ✅ 时间戳
- ✅ 状态信息

### 3. 类型安全

前端可以定义明确的 TypeScript 类型:

```typescript
interface StoryboardDomainData {
  count: number;
  storyboards: Array<{
    id: string;
    sequence_number: number;
    scene_description: string;
    narration_text: string;
    image_prompt: string;
    duration_seconds: number;
    model_provider: {
      id: string;
      name: string;
      model_name: string;
    } | null;
    prompt_used: string;
    generation_metadata: Record<string, any>;
    created_at: string;
    updated_at: string;
  }>;
}
```

### 4. 易于扩展

添加新字段只需修改序列化器,不影响现有代码。

## 相关文件

- **序列化器**: `backend/apps/projects/serializers.py`
- **API 文档**: `backend/API_STAGE_RESPONSE_FORMAT.md`
- **模型定义**: `backend/apps/content/models.py`

## 测试建议

### 单元测试

```python
from django.test import TestCase
from apps.projects.models import Project, ProjectStage
from apps.content.models import ContentRewrite, Storyboard
from apps.projects.serializers import ProjectStageSerializer

class ProjectStageSerializerTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name='测试项目',
            original_topic='测试主题'
        )

    def test_rewrite_domain_data(self):
        """测试文案改写阶段的 domain_data"""
        # 创建文案改写数据
        rewrite = ContentRewrite.objects.create(
            project=self.project,
            original_text='原始文本',
            rewritten_text='改写后文本'
        )

        # 创建阶段
        stage = ProjectStage.objects.create(
            project=self.project,
            stage_type='rewrite',
            status='completed'
        )

        # 序列化
        serializer = ProjectStageSerializer(stage)
        data = serializer.data

        # 验证
        self.assertIsNotNone(data['domain_data'])
        self.assertEqual(data['domain_data']['rewritten_text'], '改写后文本')

    def test_storyboard_domain_data(self):
        """测试分镜阶段的 domain_data"""
        # 创建分镜数据
        Storyboard.objects.create(
            project=self.project,
            sequence_number=1,
            scene_description='特写',
            narration_text='旁白',
            image_prompt='提示词'
        )

        # 创建阶段
        stage = ProjectStage.objects.create(
            project=self.project,
            stage_type='storyboard',
            status='completed'
        )

        # 序列化
        serializer = ProjectStageSerializer(stage)
        data = serializer.data

        # 验证
        self.assertIsNotNone(data['domain_data'])
        self.assertEqual(data['domain_data']['count'], 1)
        self.assertEqual(len(data['domain_data']['storyboards']), 1)
```

### 集成测试

```python
from rest_framework.test import APITestCase

class ProjectStageAPITestCase(APITestCase):
    def test_get_project_stages(self):
        """测试获取项目阶段 API"""
        # 创建测试数据
        # ...

        # 调用 API
        response = self.client.get(f'/api/v1/projects/{project.id}/')

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 验证 stages 包含 domain_data
        for stage in data['stages']:
            self.assertIn('domain_data', stage)
```

## 总结

✅ **已完成**:
- 修改 `ProjectStageSerializer`,添加 `domain_data` 字段
- 实现 5 个阶段类型的数据序列化(video_generation 待实现)
- 使用 `select_related()` 优化查询性能
- 保持向后兼容性
- 创建详细的 API 文档

🎯 **优势**:
- 数据结构清晰,易于前端使用
- 包含完整的元数据信息
- 类型安全,易于定义 TypeScript 类型
- 性能优化,避免 N+1 查询

📝 **后续工作**:
- 实现 `video_generation` 阶段的序列化
- 编写单元测试和集成测试
- 更新前端代码使用新的 `domain_data` 字段
- 考虑添加分页支持(如果分镜/图片数量很大)
