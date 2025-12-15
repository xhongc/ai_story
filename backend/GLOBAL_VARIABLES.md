# 全局变量系统使用指南

## 概述

全局变量系统允许用户定义可在所有提示词模板中使用的变量，支持用户级和系统级作用域。

## 核心特性

### 1. 变量类型
- **string**: 字符串类型
- **number**: 数字类型（整数或浮点数）
- **boolean**: 布尔值（true/false）
- **json**: JSON对象

### 2. 作用域
- **user**: 用户级变量，仅创建者可见和使用
- **system**: 系统级变量，所有用户可见（仅管理员可创建）

### 3. 变量分组
支持将变量按功能分组管理，例如：
- 品牌信息
- 风格设置
- 技术参数
- 等等

## API 接口

### 基础 CRUD

```bash
# 获取变量列表
GET /api/v1/prompts/variables/
Query params: scope, group, variable_type, is_active, search, page, page_size

# 获取变量详情
GET /api/v1/prompts/variables/{id}/

# 创建变量
POST /api/v1/prompts/variables/
Body: {
  "key": "brand_name",
  "value": "我的品牌",
  "variable_type": "string",
  "scope": "user",
  "group": "品牌信息",
  "description": "品牌名称",
  "is_active": true
}

# 更新变量
PUT /api/v1/prompts/variables/{id}/
PATCH /api/v1/prompts/variables/{id}/

# 删除变量
DELETE /api/v1/prompts/variables/{id}/
```

### 特殊操作

```bash
# 获取所有分组
GET /api/v1/prompts/variables/groups/
Response: {
  "groups": ["品牌信息", "风格设置", "技术参数"]
}

# 获取可用于模板渲染的变量字典
GET /api/v1/prompts/variables/for_template/?include_system=true
Response: {
  "variables": {
    "brand_name": "我的品牌",
    "style": "现代简约",
    "max_length": 1000
  },
  "count": 3
}

# 批量创建/更新变量
POST /api/v1/prompts/variables/batch_create/
Body: {
  "variables": [
    {
      "key": "brand_name",
      "value": "我的品牌",
      "variable_type": "string",
      "scope": "user",
      "group": "品牌信息"
    },
    {
      "key": "max_length",
      "value": "1000",
      "variable_type": "number",
      "scope": "user",
      "group": "技术参数"
    }
  ]
}
Response: {
  "created": [...],
  "updated": [...],
  "errors": [],
  "summary": {
    "created_count": 1,
    "updated_count": 1,
    "error_count": 0
  }
}

# 验证变量键是否可用
POST /api/v1/prompts/variables/validate_key/
Body: {
  "key": "my_variable",
  "scope": "user"
}
Response: {
  "valid": true,
  "message": "变量键可用"
}
```

## 在提示词模板中使用

### 基本用法

在提示词模板中，可以直接使用 `{{ variable_key }}` 语法引用全局变量：

```jinja2
请为 {{ brand_name }} 品牌创作一个 {{ style }} 风格的故事。
故事长度不超过 {{ max_length }} 字。

主题：{{ project.original_topic }}
```

### 变量优先级

当变量名冲突时，按以下优先级使用：
1. **输入数据**（最高优先级）- 来自当前阶段的输入
2. **项目信息** - project.name, project.description 等
3. **全局变量**（最低优先级）- 用户定义的全局变量

### 内置变量

系统自动提供以下内置变量：

```python
{
  'project': {
    'name': '项目名称',
    'description': '项目描述',
    'original_topic': '原始主题'
  },
  'random_seed': 123456  # 仅在文生图阶段可用
}
```

## 数据模型

### GlobalVariable 模型

```python
class GlobalVariable(models.Model):
    id = UUIDField(primary_key=True)
    key = CharField(max_length=100, db_index=True)
    value = TextField()
    variable_type = CharField(choices=['string', 'number', 'boolean', 'json'])
    scope = CharField(choices=['user', 'system'])
    group = CharField(max_length=100, blank=True)
    description = TextField(blank=True)
    is_active = BooleanField(default=True)
    created_by = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('key', 'created_by', 'scope')]
```

### 类型转换

系统会自动将变量值转换为正确的类型：

```python
# string: 直接返回字符串
"Hello World" → "Hello World"

# number: 转换为整数或浮点数
"42" → 42
"3.14" → 3.14

# boolean: 转换为布尔值
"true" → True
"false" → False
"1" → True
"0" → False

# json: 解析为Python对象
'{"name": "test"}' → {"name": "test"}
```

## 权限控制

### 用户级变量
- 创建者可以完全控制（CRUD）
- 其他用户不可见

### 系统级变量
- 仅管理员可以创建和删除
- 所有用户可见和使用
- 普通用户不能修改

## 验证规则

### 变量键（key）
- 只能包含字母、数字、下划线
- 必须以字母或下划线开头
- 不能是 Python 保留字（if, for, class 等）
- 在同一作用域下必须唯一

### 变量值（value）
- 根据 variable_type 进行格式验证
- number 类型必须是有效数字
- boolean 类型必须是 true/false/1/0/yes/no/on/off
- json 类型必须是有效的 JSON 字符串

## 使用示例

### 示例 1: 品牌信息变量

```python
# 创建品牌相关变量
variables = [
    {
        "key": "brand_name",
        "value": "AI Story",
        "variable_type": "string",
        "group": "品牌信息",
        "description": "品牌名称"
    },
    {
        "key": "brand_slogan",
        "value": "让AI讲述你的故事",
        "variable_type": "string",
        "group": "品牌信息",
        "description": "品牌口号"
    },
    {
        "key": "brand_style",
        "value": "现代科技感",
        "variable_type": "string",
        "group": "品牌信息",
        "description": "品牌风格"
    }
]
```

在提示词模板中使用：

```jinja2
请为 {{ brand_name }} 创作一个体现 "{{ brand_slogan }}" 理念的故事。
风格要求：{{ brand_style }}

故事主题：{{ project.original_topic }}
```

### 示例 2: 技术参数变量

```python
variables = [
    {
        "key": "max_story_length",
        "value": "2000",
        "variable_type": "number",
        "group": "技术参数",
        "description": "故事最大长度"
    },
    {
        "key": "enable_emoji",
        "value": "true",
        "variable_type": "boolean",
        "group": "技术参数",
        "description": "是否启用表情符号"
    },
    {
        "key": "image_config",
        "value": '{"ratio": "16:9", "quality": "high"}',
        "variable_type": "json",
        "group": "技术参数",
        "description": "图片生成配置"
    }
]
```

在提示词模板中使用：

```jinja2
请创作一个不超过 {{ max_story_length }} 字的故事。
{% if enable_emoji %}
可以适当使用表情符号增加趣味性。
{% endif %}

图片生成配置：
- 比例：{{ image_config.ratio }}
- 质量：{{ image_config.quality }}
```

### 示例 3: 系统级默认变量（管理员创建）

```python
# 管理员创建系统级变量，所有用户可用
variables = [
    {
        "key": "default_language",
        "value": "中文",
        "variable_type": "string",
        "scope": "system",
        "group": "系统设置",
        "description": "默认语言"
    },
    {
        "key": "max_retries",
        "value": "3",
        "variable_type": "number",
        "scope": "system",
        "group": "系统设置",
        "description": "最大重试次数"
    }
]
```

## 前端集成

### API 调用示例

```javascript
import { globalVariableAPI } from '@/api/prompts';

// 获取变量列表
const variables = await globalVariableAPI.getList({
  scope: 'user',
  group: '品牌信息',
  is_active: true
});

// 创建变量
await globalVariableAPI.create({
  key: 'brand_name',
  value: '我的品牌',
  variable_type: 'string',
  scope: 'user',
  group: '品牌信息',
  description: '品牌名称'
});

// 获取可用于模板的变量
const { variables: templateVars } = await globalVariableAPI.getForTemplate(true);
// templateVars = { brand_name: "我的品牌", max_length: 1000, ... }

// 批量创建
await globalVariableAPI.batchCreate([
  { key: 'var1', value: 'value1', variable_type: 'string' },
  { key: 'var2', value: '100', variable_type: 'number' }
]);

// 验证变量键
const { valid, message } = await globalVariableAPI.validateKey('my_var', 'user');
```

## 最佳实践

### 1. 变量命名
- 使用有意义的名称：`brand_name` 而不是 `bn`
- 使用下划线分隔：`max_story_length` 而不是 `maxStoryLength`
- 避免过长的名称：保持在 30 个字符以内

### 2. 变量分组
- 按功能分组：品牌信息、技术参数、风格设置等
- 保持分组名称一致性
- 不要创建过多分组（建议 5-10 个）

### 3. 变量描述
- 提供清晰的描述说明变量用途
- 说明变量的取值范围或格式要求
- 记录变量的使用场景

### 4. 类型选择
- 优先使用 string 类型（最灵活）
- 需要数值计算时使用 number
- 开关配置使用 boolean
- 复杂配置使用 json

### 5. 作用域选择
- 个人使用的变量使用 user 作用域
- 全局通用的变量由管理员创建为 system 作用域
- 避免创建过多系统级变量

## 故障排查

### 变量未生效
1. 检查变量是否激活（is_active=true）
2. 检查变量键拼写是否正确
3. 检查作用域是否正确
4. 检查是否有同名变量被覆盖

### 类型转换错误
1. 检查 variable_type 是否正确
2. 检查 value 格式是否符合类型要求
3. 对于 json 类型，确保是有效的 JSON 字符串

### 权限错误
1. 系统级变量只能由管理员创建
2. 用户只能修改自己创建的变量
3. 检查用户是否有相应权限

## 技术实现

### 渲染流程

1. **获取全局变量**
   ```python
   global_vars = await GlobalVariable.get_variables_for_user(
       user=user,
       include_system=True
   )
   ```

2. **合并变量**
   ```python
   template_vars = {
       **global_vars,  # 全局变量（最低优先级）
       'project': {...},
       **input_data  # 输入数据（最高优先级）
   }
   ```

3. **渲染模板**
   ```python
   jinja_template = Template(template_content)
   rendered = jinja_template.render(**template_vars)
   ```

### 性能优化

- 使用数据库索引加速查询
- 缓存常用的系统级变量
- 批量操作减少数据库访问
- 异步获取变量提高性能

## 未来扩展

### 计划功能
- [ ] 变量版本控制
- [ ] 变量使用统计
- [ ] 变量导入/导出
- [ ] 变量模板（预设变量集）
- [ ] 变量依赖关系
- [ ] 变量值的表达式计算

### 可能的改进
- 支持更多数据类型（日期、数组等）
- 支持变量继承和覆盖
- 支持变量的条件渲染
- 支持变量的国际化
