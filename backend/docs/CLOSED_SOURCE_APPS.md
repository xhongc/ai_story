# 闭源模块发布说明

`backend/apps/agent` 和 `backend/apps/mcp` 支持通过 Cython 生成编译产物，当前仓库允许同时保留源码和 `.so`/`.pyd` 文件。

## 编译命令

在 Docker 容器或本地后端环境中执行：

```bash
cd /app/backend
python manage.py setup_in_docker
```

命令行为：

1. 仅扫描 `backend/apps/agent`、`backend/apps/mcp`。
2. 仅编译普通 `.py` 文件，自动跳过 `__init__.py`、`migrations`、`tests`、`__pycache__`。
3. 生成 `.so` 或 `.pyd` 后会清理中间 `.c` 和 `build/` 目录。
4. 不删除原始 `.py` 源码。

## 本地开发

1. 将闭源源码放到单独私有 Git 仓库，并保持与主仓库一致的包结构：`backend/apps/agent`、`backend/apps/mcp`。
2. 在本地环境设置 `PRIVATE_BACKEND_APPS_ROOT=/absolute/path/to/private_repo/backend/apps`。
3. Django 导入 `apps.agent`、`apps.mcp` 时，会优先从 `PRIVATE_BACKEND_APPS_ROOT` 加载源码；未配置时，再回退到当前仓库内的编译产物。

## 发布约束

1. 当前仓库中的 `backend/apps/agent`、`backend/apps/mcp` 允许同时保留源码和编译产物。
2. 如果后续切换回纯编译产物发布模式，需要同步调整检查脚本和本说明。
3. 构建完成后，可按需提交源码与编译产物，或仅在发布流程中使用编译产物。

## 检查命令

```bash
bash scripts/check_closed_source_apps.sh
```

如果你仍在使用旧版检查脚本，需要注意它可能默认要求目录内只保留 `.so` 文件：

- `backend/apps/agent`
- `backend/apps/mcp`

## 注意事项

- `.gitignore` 只负责忽略未跟踪文件，已经被 Git 跟踪的源码仍需迁移出仓库历史或手动删除后再提交。
- 私有仓库建议保持与主仓库相同的 Python 包名，避免改动 Django `INSTALLED_APPS`、路由和导入路径。
