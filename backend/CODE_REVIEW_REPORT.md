# Code Review 报告 - 流程记录格式优化

## 审查概述

本次代码审查针对流程记录格式优化的重构代码,从以下几个维度进行评估:
- ✅ 模型定义的完整性和一致性
- ✅ 数据流转逻辑的正确性
- ⚠️ 潜在的性能问题
- ⚠️ 错误处理和边界情况
- ⚠️ 向后兼容性问题

---

## 🟢 优点 (Strengths)

### 1. 架构设计优秀

**单一职责原则 (SRP)**
- ✅ 每个模型只负责一种业务数据
- ✅ `ProjectStage` 只负责阶段状态追踪
- ✅ 领域模型负责具体业务数据存储

**数据流转清晰**
```
Project → ContentRewrite → Storyboard → GeneratedImage/CameraMovement
```
- ✅ 通过外键建立明确的依赖关系
- ✅ 消除了数据冗余
- ✅ 易于理解和维护

### 2. 模型设计合理

**字段完整性**
- ✅ 所有模型都包含必要的元数据字段 (`model_provider`, `prompt_used`, `generation_metadata`)
- ✅ 时间戳字段完整 (`created_at`, `updated_at`)
- ✅ 外键关系正确设置 (`on_delete=models.CASCADE/SET_NULL`)

**索引优化**
- ✅ `Storyboard` 模型有 `unique_together` 约束
- ✅ 添加了复合索引 `Index(fields=['project', 'sequence_number'])`

### 3. 代码质量良好

**类型注解**
- ✅ 方法参数和返回值都有类型注解
- ✅ 使用 `Optional`, `Dict`, `List` 等类型提示

**文档字符串**
- ✅ 所有方法都有详细的 docstring
- ✅ 参数和返回值说明清晰

---

## 🟡 需要改进的问题 (Issues)

### 1. ⚠️ **严重问题**: AI客户端没有 `provider` 属性

**位置**: `llm_stage.py:440, 465, 513`

**问题代码**:
```python
ai_client = self._get_ai_client(project)
provider = ai_client.provider if hasattr(ai_client, 'provider') else None
```

**问题分析**:
- `BaseAIClient` 类没有 `provider` 属性
- `create_ai_client()` 工厂函数接收 `ModelProvider` 对象,但不会将其存储到客户端实例中
- 当前代码会导致 `provider` 始终为 `None`

**影响**:
- 保存到数据库的 `model_provider` 字段将为 `NULL`
- 无法追踪哪个模型提供商生成了数据
- 元数据不完整

**修复方案**:

**方案1: 修改 BaseAIClient 基类** (推荐)
```python
# core/ai_client/base.py
class BaseAIClient(ABC):
    def __init__(self, api_url: str, api_key: str, model_name: str, provider=None, **kwargs):
        self.api_url = api_url
        self.api_key = api_key
        self.model_name = model_name
        self.provider = provider  # 添加这一行
        self.config = kwargs
```

**方案2: 修改工厂函数**
```python
# core/ai_client/factory.py
def create_ai_client(provider) -> BaseAIClient:
    # ... 现有代码 ...

    client = executor_class(
        api_url=provider.api_url,
        api_key=provider.api_key,
        model_name=provider.model_name,
        provider=provider,  # 传递 provider 对象
        **config
    )

    return client
```

**方案3: 直接使用 provider 对象** (最简单)
```python
# llm_stage.py
def _save_result(self, project, stage, generated_text, prompt_used, metadata):
    from apps.content.models import ContentRewrite

    # 直接获取 provider,不从 ai_client 获取
    provider = self._get_ai_client_provider(project)

    ContentRewrite.objects.update_or_create(
        project=project,
        defaults={
            'original_text': project.original_topic,
            'rewritten_text': generated_text,
            'prompt_used': prompt_used,
            'model_provider': provider,  # 直接使用
            'generation_metadata': metadata
        }
    )

def _get_ai_client_provider(self, project):
    """获取模型提供商对象"""
    config = getattr(project, 'model_config', None)

    if config:
        provider_field_map = {
            'rewrite': 'rewrite_providers',
            'storyboard': 'storyboard_providers',
            'camera_movement': 'camera_providers',
        }
        field_name = provider_field_map.get(self.stage_type)
        if field_name:
            providers = list(getattr(config, field_name).all())
            if providers:
                return providers[0]

    # 从提示词模板获取
    template = self._get_prompt_template(project)
    if template and template.model_provider:
        return template.model_provider

    # 获取默认提供商
    return self._get_default_provider()
```

---

### 2. ⚠️ **性能问题**: N+1 查询

**位置**: `text2image_stage.py:142-148`

**问题代码**:
```python
storyboards_query = StoryboardModel.objects.filter(project=project).order_by('sequence_number')

if storyboard_ids:
    storyboards_query = storyboards_query.filter(sequence_number__in=storyboard_ids)

storyboards = list(storyboards_query)
```

**问题分析**:
- 没有使用 `select_related()` 预加载关联的 `model_provider`
- 后续访问 `storyboard.model_provider` 会产生额外的数据库查询

**修复方案**:
```python
storyboards_query = StoryboardModel.objects.filter(
    project=project
).select_related('model_provider').order_by('sequence_number')
```

---

### 3. ⚠️ **性能问题**: 循环中的数据库操作

**位置**: `llm_stage.py:470-487`

**问题代码**:
```python
for scene in scenes:
    storyboard, created = Storyboard.objects.update_or_create(
        project=project,
        sequence_number=scene['scene_number'],
        defaults={...}
    )
    created_ids.append(str(storyboard.id))
```

**问题分析**:
- 在循环中逐个创建/更新分镜
- 如果有10个分镜,就会执行10次数据库操作
- 无法利用批量操作优化

**修复方案**:
```python
# 使用 bulk_create 和 bulk_update
storyboards_to_create = []
storyboards_to_update = []

# 先查询已存在的分镜
existing_storyboards = {
    sb.sequence_number: sb
    for sb in Storyboard.objects.filter(
        project=project,
        sequence_number__in=[s['scene_number'] for s in scenes]
    )
}

for scene in scenes:
    scene_number = scene['scene_number']

    if scene_number in existing_storyboards:
        # 更新现有分镜
        sb = existing_storyboards[scene_number]
        sb.scene_description = scene.get('shot_type', '')
        sb.narration_text = scene.get('narration', '')
        sb.image_prompt = scene.get('visual_prompt', '')
        sb.duration_seconds = scene.get('duration', 3.0)
        sb.model_provider = provider
        sb.prompt_used = prompt_used
        sb.generation_metadata = {...}
        storyboards_to_update.append(sb)
    else:
        # 创建新分镜
        storyboards_to_create.append(Storyboard(
            project=project,
            sequence_number=scene_number,
            scene_description=scene.get('shot_type', ''),
            narration_text=scene.get('narration', ''),
            image_prompt=scene.get('visual_prompt', ''),
            duration_seconds=scene.get('duration', 3.0),
            model_provider=provider,
            prompt_used=prompt_used,
            generation_metadata={...}
        ))

# 批量操作
if storyboards_to_create:
    Storyboard.objects.bulk_create(storyboards_to_create)

if storyboards_to_update:
    Storyboard.objects.bulk_update(
        storyboards_to_update,
        fields=['scene_description', 'narration_text', 'image_prompt',
                'duration_seconds', 'model_provider', 'prompt_used',
                'generation_metadata']
    )
```

---

### 4. ⚠️ **错误处理**: 异常捕获过于宽泛

**位置**: `llm_stage.py:522-525`

**问题代码**:
```python
try:
    from apps.projects.utils import parse_json
    camera_data = parse_json(generated_text)
    movement_type = camera_data.get('movement_type', '')
    movement_params = camera_data.get('params', {})
except:
    # 如果解析失败,将整个文本作为参数存储
    movement_type = ''
    movement_params = {'raw_text': generated_text}
```

**问题分析**:
- 使用裸 `except:` 会捕获所有异常,包括 `KeyboardInterrupt`, `SystemExit`
- 无法区分不同类型的错误
- 没有记录日志

**修复方案**:
```python
try:
    from apps.projects.utils import parse_json
    camera_data = parse_json(generated_text)

    if not camera_data or not isinstance(camera_data, dict):
        raise ValueError("解析结果为空或格式错误")

    movement_type = camera_data.get('movement_type', '')
    movement_params = camera_data.get('params', {})

except (ValueError, KeyError, TypeError) as e:
    # 记录解析失败的原因
    logger.warning(
        f"运镜数据解析失败: {str(e)}, "
        f"将原始文本存储到 movement_params"
    )
    movement_type = ''
    movement_params = {'raw_text': generated_text}
```

---

### 5. ⚠️ **向后兼容性**: 缺少数据迁移逻辑

**问题分析**:
- 旧数据仍存储在 `ProjectStage.output_data` 中
- 新代码从领域模型读取数据
- 如果领域模型中没有数据,会抛出异常

**影响**:
- 现有项目无法继续执行后续阶段
- 需要手动迁移数据或重新生成

**修复方案**:

**方案1: 添加 fallback 逻辑**
```python
def _get_input_data(self, project: Project, stage: ProjectStage) -> Dict[str, Any]:
    """获取输入数据,支持从旧数据源 fallback"""
    from apps.content.models import ContentRewrite, Storyboard

    if self.stage_type == 'storyboard':
        # 优先从 ContentRewrite 模型读取
        try:
            content_rewrite = ContentRewrite.objects.get(project=project)
            return {
                'raw_text': content_rewrite.rewritten_text,
                'human_text': ''
            }
        except ContentRewrite.DoesNotExist:
            # Fallback: 从旧的 ProjectStage 读取
            logger.warning(f"项目 {project.id} 未找到 ContentRewrite,尝试从 ProjectStage 读取")
            rewrite_stage = ProjectStage.objects.filter(
                project=project,
                stage_type='rewrite',
                status='completed'
            ).first()

            if rewrite_stage and rewrite_stage.output_data:
                return {
                    'raw_text': rewrite_stage.output_data.get('raw_text', ''),
                    'human_text': ''
                }

            raise ValueError("前置阶段(文案改写)未完成或无输出数据")
```

**方案2: 编写数据迁移脚本**
```python
# backend/migrate_old_data.py
def migrate_project_data(project_id):
    """将旧的 ProjectStage 数据迁移到领域模型"""
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
                'prompt_used': '',
                'model_provider': None
            }
        )

    # 2. 迁移分镜数据
    storyboard_stage = ProjectStage.objects.filter(
        project=project,
        stage_type='storyboard'
    ).first()

    if storyboard_stage and storyboard_stage.output_data:
        scenes = storyboard_stage.output_data.get('human_text', {}).get('scenes', [])
        for scene in scenes:
            Storyboard.objects.get_or_create(
                project=project,
                sequence_number=scene['scene_number'],
                defaults={
                    'scene_description': scene.get('shot_type', ''),
                    'narration_text': scene.get('narration', ''),
                    'image_prompt': scene.get('visual_prompt', ''),
                    'duration_seconds': scene.get('duration', 3.0)
                }
            )

    # 3. 迁移图片数据
    # ... 类似逻辑
```

---

### 6. ⚠️ **边界情况**: 空数据处理不完善

**位置**: `llm_stage.py:273-280`

**问题代码**:
```python
scenes = []
for sb in storyboards:
    scenes.append({
        'scene_number': sb.sequence_number,
        'narration': sb.narration_text,
        'visual_prompt': sb.image_prompt,
        'shot_type': sb.scene_description
    })
```

**问题分析**:
- 如果 `narration_text` 或 `image_prompt` 为空字符串,可能导致后续处理失败
- 没有验证必填字段

**修复方案**:
```python
scenes = []
for sb in storyboards:
    # 验证必填字段
    if not sb.narration_text or not sb.image_prompt:
        logger.warning(
            f"分镜 {sb.sequence_number} 缺少必填字段: "
            f"narration_text={bool(sb.narration_text)}, "
            f"image_prompt={bool(sb.image_prompt)}"
        )
        continue

    scenes.append({
        'scene_number': sb.sequence_number,
        'narration': sb.narration_text,
        'visual_prompt': sb.image_prompt,
        'shot_type': sb.scene_description
    })

if not scenes:
    raise ValueError("没有有效的分镜数据")
```

---

### 7. ⚠️ **代码重复**: 获取 provider 的逻辑重复

**位置**: `llm_stage.py:440, 465, 513` 和 `text2image_stage.py:313`

**问题分析**:
- 多处使用相同的逻辑获取 `provider`
- 代码重复,不易维护

**修复方案**:
```python
def _get_current_provider(self, project: Project) -> Optional[ModelProvider]:
    """
    获取当前阶段使用的模型提供商

    优先级:
    1. 项目模型配置
    2. 提示词模板配置
    3. 系统默认提供商
    """
    # 1. 从项目模型配置获取
    config = getattr(project, 'model_config', None)

    if config:
        provider_field_map = {
            'rewrite': 'rewrite_providers',
            'storyboard': 'storyboard_providers',
            'camera_movement': 'camera_providers',
            'image_generation': 'image_providers',
        }

        field_name = provider_field_map.get(self.stage_type)
        if field_name:
            providers = list(getattr(config, field_name).all())
            if providers:
                return providers[0]

    # 2. 从提示词模板获取
    template = self._get_prompt_template(project)
    if template and template.model_provider:
        return template.model_provider

    # 3. 获取系统默认提供商
    return self._get_default_provider()

# 然后在 _save_result 中使用
def _save_result(self, project, stage, generated_text, prompt_used, metadata):
    provider = self._get_current_provider(project)

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

---

### 8. ⚠️ **数据一致性**: 缺少事务保护

**位置**: `llm_stage.py:470-487`

**问题代码**:
```python
for scene in scenes:
    storyboard, created = Storyboard.objects.update_or_create(...)
    created_ids.append(str(storyboard.id))

return {
    'status': 'completed',
    'storyboard_count': len(created_ids),
    'storyboard_ids': created_ids
}
```

**问题分析**:
- 如果中途某个分镜创建失败,已创建的分镜不会回滚
- 可能导致数据不完整

**修复方案**:
```python
from django.db import transaction

@transaction.atomic
def _save_result(self, project, stage, generated_text, prompt_used, metadata):
    """使用事务保证数据一致性"""
    if self.stage_type == 'storyboard':
        storyboard_data = parse_storyboard_json(generated_text)
        scenes = storyboard_data.get('scenes', [])

        provider = self._get_current_provider(project)

        created_ids = []
        for scene in scenes:
            storyboard, created = Storyboard.objects.update_or_create(
                project=project,
                sequence_number=scene['scene_number'],
                defaults={...}
            )
            created_ids.append(str(storyboard.id))

        return {
            'status': 'completed',
            'storyboard_count': len(created_ids),
            'storyboard_ids': created_ids
        }
```

---

## 🔵 建议 (Recommendations)

### 1. 添加模型方法

为领域模型添加便捷方法:

```python
# apps/content/models.py
class Storyboard(models.Model):
    # ... 现有字段 ...

    def get_latest_image(self):
        """获取最新生成的图片"""
        return self.images.filter(status='completed').order_by('-created_at').first()

    def has_camera_movement(self):
        """检查是否有运镜数据"""
        return hasattr(self, 'camera_movement')

    def is_ready_for_video(self):
        """检查是否准备好生成视频"""
        return (
            self.images.filter(status='completed').exists() and
            self.has_camera_movement()
        )
```

### 2. 添加数据验证

在模型层添加验证逻辑:

```python
class Storyboard(models.Model):
    # ... 现有字段 ...

    def clean(self):
        """模型验证"""
        from django.core.exceptions import ValidationError

        if not self.narration_text:
            raise ValidationError({'narration_text': '旁白文案不能为空'})

        if not self.image_prompt:
            raise ValidationError({'image_prompt': '文生图提示词不能为空'})

        if self.duration_seconds <= 0:
            raise ValidationError({'duration_seconds': '时长必须大于0'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

### 3. 添加查询优化方法

创建管理器方法优化常用查询:

```python
class StoryboardManager(models.Manager):
    def with_related(self):
        """预加载关联数据"""
        return self.select_related(
            'project',
            'model_provider'
        ).prefetch_related(
            'images',
            'camera_movement'
        )

    def ready_for_video(self, project):
        """获取准备好生成视频的分镜"""
        return self.filter(
            project=project,
            images__status='completed'
        ).exclude(
            camera_movement__isnull=True
        ).distinct()

class Storyboard(models.Model):
    objects = StoryboardManager()
    # ... 其他字段 ...
```

### 4. 添加信号处理

使用 Django 信号自动维护数据:

```python
# apps/content/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Storyboard, GeneratedImage

@receiver(post_save, sender=Storyboard)
def update_project_stage_on_storyboard_save(sender, instance, created, **kwargs):
    """分镜保存后更新项目阶段状态"""
    if created:
        project = instance.project
        stage = ProjectStage.objects.filter(
            project=project,
            stage_type='storyboard'
        ).first()

        if stage:
            # 更新统计数据
            total_count = Storyboard.objects.filter(project=project).count()
            stage.output_data = {
                'status': 'completed',
                'storyboard_count': total_count
            }
            stage.save()
```

### 5. 添加单元测试

为关键逻辑编写测试:

```python
# apps/content/tests/test_processors.py
from django.test import TestCase
from apps.content.processors.llm_stage import LLMStageProcessor
from apps.content.models import ContentRewrite, Storyboard

class LLMStageProcessorTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name='测试项目',
            original_topic='测试主题'
        )
        self.processor = LLMStageProcessor('rewrite')

    def test_save_rewrite_result(self):
        """测试保存文案改写结果"""
        result = self.processor._save_result(
            project=self.project,
            stage=None,
            generated_text='改写后的文本',
            prompt_used='测试提示词',
            metadata={}
        )

        # 验证结果
        self.assertEqual(result['status'], 'completed')

        # 验证数据库
        rewrite = ContentRewrite.objects.get(project=self.project)
        self.assertEqual(rewrite.rewritten_text, '改写后的文本')
        self.assertEqual(rewrite.prompt_used, '测试提示词')
```

---

## 📊 优先级评估

### 🔴 高优先级 (必须修复)

1. **AI客户端 provider 属性问题** - 导致元数据丢失
2. **向后兼容性问题** - 影响现有项目

### 🟡 中优先级 (建议修复)

3. **N+1 查询问题** - 影响性能
4. **循环中的数据库操作** - 影响性能
5. **异常捕获过于宽泛** - 影响调试

### 🟢 低优先级 (可选优化)

6. **代码重复** - 影响可维护性
7. **缺少事务保护** - 潜在的数据一致性风险
8. **边界情况处理** - 提升健壮性

---

## 📝 总结

### 整体评价

本次重构在架构设计和代码组织方面做得非常好,成功实现了:
- ✅ 数据结构清晰化
- ✅ 消除数据冗余
- ✅ 遵循设计原则

但存在一些需要修复的问题,主要集中在:
- ⚠️ AI客户端 provider 属性缺失
- ⚠️ 性能优化不足
- ⚠️ 向后兼容性考虑不足

### 建议的修复顺序

1. **立即修复**: AI客户端 provider 属性问题
2. **短期修复**: 添加向后兼容性支持
3. **中期优化**: 性能优化(N+1查询、批量操作)
4. **长期改进**: 添加测试、信号处理、查询优化

### 代码质量评分

- **架构设计**: ⭐⭐⭐⭐⭐ (5/5)
- **代码质量**: ⭐⭐⭐⭐ (4/5)
- **性能优化**: ⭐⭐⭐ (3/5)
- **错误处理**: ⭐⭐⭐ (3/5)
- **向后兼容**: ⭐⭐ (2/5)

**总体评分**: ⭐⭐⭐⭐ (4/5)

---

## 🔧 快速修复清单

```python
# 1. 修复 AI客户端 provider 属性
# 在 llm_stage.py 中添加新方法
def _get_current_provider(self, project):
    # ... 实现代码 ...

# 2. 添加 select_related 优化
storyboards = StoryboardModel.objects.filter(
    project=project
).select_related('model_provider').order_by('sequence_number')

# 3. 添加向后兼容性
try:
    content_rewrite = ContentRewrite.objects.get(project=project)
    return {'raw_text': content_rewrite.rewritten_text}
except ContentRewrite.DoesNotExist:
    # Fallback to old data
    rewrite_stage = ProjectStage.objects.filter(...)
    # ...

# 4. 改进异常处理
except (ValueError, KeyError, TypeError) as e:
    logger.warning(f"解析失败: {str(e)}")
    # ...

# 5. 添加事务保护
from django.db import transaction

@transaction.atomic
def _save_result(self, ...):
    # ...
```
