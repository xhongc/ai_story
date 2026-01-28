# AI Story生成系统 - 后端框架

## 项目概述

这是一个基于Django 3.2.15的AI Story生成系统后端,严格遵循SOLID、KISS、DRY、YAGNI原则,采用分层架构设计。

## 技术栈

- **框架**: Django 3.2.15 + Django REST Framework
- **异步**: Celery + Redis
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **容器化**: Docker + Docker Compose

## 项目结构

```
backend/
├── config/                    # Django配置
│   ├── settings/             # 分层设置(base/development/production)
│   ├── urls.py               # 主路由
│   ├── asgi.py               # ASGI配置
│   ├── wsgi.py               # WSGI配置
│   └── celery.py             # Celery配置
│
├── apps/                     # 应用模块
│   ├── projects/            # 项目管理
│   ├── prompts/             # 提示词管理
│   ├── models/              # AI模型管理
│   ├── content/             # 内容生成
│   └── users/               # 用户管理
│
├── core/                     # 核心抽象
│   ├── ai_client/           # AI客户端抽象层
│   │   ├── base.py          # 抽象基类
│   │   ├── openai_client.py
│   │   ├── text2image_client.py
│   │   └── image2video_client.py
│   │
│   └── pipeline/            # 工作流引擎
│       ├── base.py          # Pipeline抽象
│       └── orchestrator.py  # 编排器
│
│
└── manage.py                # Django管理脚本
```

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
cd backend
pip install -r requirements/development.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp ../.env.example ../.env

# 编辑.env文件,配置必要的环境变量
```

### 3. 初始化数据库

```bash
# 执行迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

### 4. 启动开发服务器

```bash
# 启动Django开发服务器
python manage.py runserver

# 启动Celery Worker (新终端)
celery -A config worker -l info

# 启动Celery Beat (新终端)
celery -A config beat -l info
```

### 5. 访问后台

访问 http://localhost:8000/admin 使用超级用户登录

## 使用Docker

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 执行数据库迁移
docker-compose exec backend python manage.py migrate

# 创建超级用户
docker-compose exec backend python manage.py createsuperuser

# 停止服务
docker-compose down
```

## 核心设计原则

### SOLID原则

- **单一职责(SRP)**: 每个模型、处理器只负责一项功能
- **开闭原则(OCP)**: 通过继承扩展功能,无需修改核心代码
- **里氏替换(LSP)**: AI客户端可互相替换
- **接口隔离(ISP)**: 接口专一,避免胖接口
- **依赖倒置(DIP)**: 依赖抽象接口,而非具体实现

### 其他原则

- **KISS**: 保持简单,避免过度设计
- **DRY**: 代码复用,杜绝重复
- **YAGNI**: 只实现当前需要的功能

## 领域模型

### 项目管理域
- `Project`: 项目聚合根
- `ProjectStage`: 项目阶段状态追踪
- `ProjectModelConfig`: 项目模型配置

### 提示词管理域
- `PromptTemplateSet`: 提示词集
- `PromptTemplate`: 提示词模板

### 模型管理域
- `ModelProvider`: AI模型提供商
- `ModelUsageLog`: 模型使用日志

### 内容生成域
- `ContentRewrite`: 文案改写
- `Storyboard`: 分镜
- `GeneratedImage`: 生成图片
- `CameraMovement`: 运镜
- `GeneratedVideo`: 生成视频

## Pipeline工作流

系统使用责任链模式实现工作流:

```python
from core.pipeline import ProjectPipeline, PipelineContext
from apps.content.processors.rewrite import RewriteProcessor

# 创建Pipeline
pipeline = ProjectPipeline(stages=[
    RewriteProcessor(),
    # StoryboardProcessor(),
    # ImageGenerationProcessor(),
    # CameraMovementProcessor(),
    # VideoGenerationProcessor(),
])

# 执行工作流
context = await pipeline.execute(project_id='xxx')
```

## API文档

API端点遵循RESTful规范:

- `/api/v1/projects/` - 项目管理
- `/api/v1/prompts/` - 提示词管理
- `/api/v1/models/` - 模型管理
- `/api/v1/content/` - 内容生成

详细API文档启动服务后访问: http://localhost:8000/api/docs/

## 开发规范

### 代码风格

```bash
# 格式化代码
black .

# 代码检查
flake8 .
```

### 测试

```bash
# 运行测试
pytest

# 覆盖率报告
pytest --cov=apps --cov=core
```

## 下一步工作

根据README的实施计划,接下来需要:

1. ✅ 基础框架搭建 (已完成)
2. ✅ 核心领域模型 (已完成)
3. ✅ AI客户端抽象层 (已完成)
4. ✅ Pipeline架构 (已完成)
5. ⏳ RESTful API实现 (待实现)
6. ⏳ 完整的处理器实现 (待实现)
7. ⏳ 前端开发 (待实现)

## 许可证

MIT License
