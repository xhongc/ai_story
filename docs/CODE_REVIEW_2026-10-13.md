# 代码审查报告

**审查日期**：2026-10-13
**审查范围**：`ai_story/backend`（Django 后端）、`ai_story/frontend`（Vue2 旧管理后台）、`linknow/tapnow-studio`（React 画布前端）
**规模**：后端 197 个 Python 文件 / 约 3.8 万行；两个前端各自数千行
**方法**：全量结构扫描 + 分区域深读 + 对每条结论回读源码逐行核实

> 标记说明：**【已核实】** = 已回读源码确认；【待确认】= 疑似但未完全确认。
> 本报告只列实际看到的问题，不凑数。

---

## 一、结论摘要

项目整体架构清晰（分层 settings、core 共享层、app 边界明确），但存在**若干会导致数据不一致或越权的硬伤**，以及**大量"看起来对但实际不生效"的代码**（状态判断恒真、TODO 未实现却返回成功、`await` 同步函数、bare except 吞掉必然失败的写库）。

最值得优先处理的是三类：

1. **越权/泄露**：回调接口可伪造、API Key 明文回传、模板渲染非沙箱。
2. **状态机被写坏**：`retry_stage` 把状态置为 processing 却不触发任务，阶段永久卡死。
3. **静默失效**：多处 `except: pass` 让"本该报错"的路径变成"静默丢数据"。

---

## 二、高危问题（建议本周修复）

### 1. 【已核实】回调接口存在越权写入（IDOR）
`backend/apps/workflows/serializers.py:654-692`、`backend/apps/workflows/views.py:554-588`

`WorkflowCallbackEventViewSet` 只有 `IsAuthenticated`，`get_queryset()` 按当前用户过滤，但 `create()` 走的 `validate()` 是**全局查库**，完全不校验归属：

```python
workflow_run = WorkflowRun.objects.filter(id=workflow_run_id).first()
node_run = WorkflowNodeRun.objects.filter(external_task_id=attrs['external_task_id']).order_by('-created_at').first()
```

任何登录用户只要猜到/遍历 `workflow_run_id` 或 `external_task_id`，就能伪造回调事件，经 `apply_workflow_node_result()` 改写他人项目的节点数据。

**建议**：`validate()` 内统一以 `request.user` 过滤（`project__user=user`），或改为按 `idempotency_key` + 归属双重校验。

### 2. 【已核实】模型 Provider 的 API Key 明文回传前端
`backend/apps/models/models.py:64`、`backend/apps/models/serializers.py:66,82-85`

字段注释写着"后续加密存储"，但从未加密；序列化器里写着"隐藏API Key的完整内容"，实际是**原样返回**：

```python
def to_representation(self, instance):
    """隐藏API Key的完整内容"""
    data = super().to_representation(instance)
    return data          # ← 什么都没做
```

`ModelProviderDetailSerializer.Meta.fields` 含 `api_key`，被 `views.py` 的 retrieve/create/update 复用。任意登录用户可拿到全部上游模型密钥。

**建议**：DB 层用 `cryptography.Fernet` 加密存储；输出统一走 masked（如 `sk-****1234`），仅"写入"时接受明文。

### 3. 【已核实】`retry_stage` 把阶段置为 processing 却不触发任务 → 永久卡死
`backend/apps/projects/views.py:1545-1566`

```python
stage.status = "processing"
stage.started_at = timezone.now()
stage.save()

# TODO: 调用Celery任务
# execute_project_stage.delay(str(project.id), stage_name)

return Response({"message": f"阶段 ... 开始重试"})
```

接口返回 200 并提示"开始重试"，但没有任何任务被投递。前端会一直显示"处理中"，且该阶段无法再被正常触发（状态已是 processing）。

**建议**：补上投递逻辑（或临时改为返回 501 并保留原状态），并给 `status` 增加超时自愈。

### 4. 【已核实】SSE 鉴权对象用错 → 取不到用户凭据
`backend/apps/projects/views.py:454-537`

端点声明 `permission_classes=[AllowAny]`，通过 query 里的 `access_token` 手动解析出 `user` 变量并校验了归属，但真正使用时传的是 `request.user`：

```python
user = self._authenticate_stream_user(request)   # 手动解析出的真实用户
...
ai_client = create_ai_client_for_user(provider, user=request.user)   # ← AllowAny 下是 AnonymousUser
```

`AllowAny` 下 `request.user` 是 `AnonymousUser`，会取错/取不到用户级模型配置。

**建议**：改为 `user=user`。

### 5. 【已核实】`await` 一个同步方法 → 接口必然 500
`backend/apps/prompts/views.py:503,514`、`backend/apps/prompts/models.py:234`

```python
async def for_template(self, request):           # views.py:503
    variables = await GlobalVariable.get_variables_for_user(...)   # :514
```

而 `get_variables_for_user` 是普通 `def` classmethod（返回 dict）。`await dict` 抛 `TypeError: object dict can't be used in 'await' expression`。该接口 100% 报错。

**建议**：去掉 `await`，或把模型方法改 `sync_to_async` 包装。

### 6. 【已核实】Jinja2 非沙箱渲染用户模板（SSTI）
`backend/apps/prompts/views.py:17,348`、`apps/prompts/debug_services.py:20,137`、`apps/content/processors/llm_stage.py:12,434`、`apps/content/processors/text2image_stage.py:18`

全项目统一 `from jinja2 import Template`，直接渲染用户创建的 `template_content`。用户可在模板里写 `{{ ''.__class__.__mro__[1].__subclasses__() }}` 执行任意代码。

**建议**：改用 `jinja2.sandbox.SandboxedEnvironment`，并限制可访问属性。

### 7. 【已核实】图片/视频阶段"失败也标记成功"
`backend/apps/content/processors/image2video_stage.py:324`

```python
stage.status = "completed" if failed_count == 0 else "completed"
```

两个分支完全相同，`failed_count > 0` 时仍写 `completed`，下游（分集状态、前端轮询）会误判整段成功。

**建议**：改为 `else "failed"`（或 `"partial_failed"`）。

### 8. 【已核实】失败记录写库传错类型 + 裸 `except: pass` → 失败永不落库
`backend/apps/content/processors/text2image_stage.py:836-846`

```python
except Exception as e:
    logger.error(...)
    try:
        GeneratedImage.objects.create(storyboard=storyboard, ...)   # storyboard 是 dict！
    except:
        pass
```

该函数作用域内 `storyboard` 是 dict（同函数内大量 `storyboard.get('scene_number')`），而 `GeneratedImage.storyboard` 是 `ForeignKey`（`apps/content/models.py:117`）。赋值必然抛 `ValueError`，又被裸 `except` 吞掉 → **失败记录永远写不进去，且无任何日志**。

**建议**：传 `storyboard_obj`（Storyboard 实例）；至少把裸 except 改为 `logger.exception`。

### 9. 【已核实】生产配置 `ALLOWED_HOSTS=['*']` + `CORS_ALLOW_ALL_ORIGINS=True`
`backend/config/settings/production.py:8,11`

```python
DEBUG = False
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True
```

生产环境任意 Host 头、任意来源跨域可访问。

**建议**：从环境变量读白名单。

### 10. 【已核实】Celery 与 Web 使用**不同 settings**，可能连不同数据库
`backend/config/celery_app.py:12` vs `backend/manage.py:7`

```python
# celery_app.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
# manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
```

`base` 走 `build_database_config()`（有 `MYSQL_*` 环境变量时用 MySQL），`development` 硬编码 SQLite。**worker 和 web 可能读写两个不同的库**，任务与页面数据完全对不上，且这种 bug 极难排查。

同时 `base.py:15` 硬编码 `DEBUG = True`，被 worker 长期继承。

**建议**：统一入口（都用 `production`/`development` 环境变量控制），`DEBUG` 只在最外层按环境变量设置。

### 11. 【已核实】`SECRET_KEY` 有可预测兜底值，且被用于签发 JWT
`backend/config/settings/base.py:14,207`

```python
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')
...
SIMPLE_JWT = { 'SIGNING_KEY': SECRET_KEY, ... }
```

未设置环境变量时，攻击者可用公开的默认 key 伪造任意用户 JWT。

**建议**：无环境变量时直接 `raise ImproperlyConfigured`（生产）。

### 12. 【已核实】文件上传无任何校验
`backend/apps/ai_proxy/views.py:515-561`

```python
file_content = file.read()                       # 全量入内存，无大小限制
if content_type.startswith('image/'):            # 信任客户端声明的 content_type
    ...
else:
    _, relative_path = video_storage.save_file(filename, file_content)   # 非图片一律当视频
```

无大小上限、无后缀/MIME 白名单、`content_type` 由客户端提供、文件名直接来自客户端。

**建议**：限制大小（如 100MB）、按 magic number 校验类型、对 `filename` 做 `secure_filename`。

### 13. 【已核实】JWT 放进 URL query 参数
`linknow/tapnow-studio/src/services/agentService.js:94`（以及 `ai_story/frontend/src/api/agent.js`、`api/projects.js` 同类写法）

```javascript
url.searchParams.set('access_token', accessToken);
```

Token 会进入浏览器历史、`Referer`、Nginx 访问日志、CDN 日志。SSE 确实无法带自定义 Header，但也应改用**短时效一次性 stream_token**（后端已有此机制，见 `node_chat_init`），而不是把长期 access_token 挂 URL 上。

---

## 三、中危问题

### 后端

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 14 | 【已核实】`apps/content/views.py:93` | `str(resolved_path).startswith(str(storage_root))` 前缀校验 | 同级目录 `storageX` 可通过；且存在性检查用未 resolve 的 `image_path`，两套路径不一致。应改 `Path.is_relative_to()` |
| 15 | 【已核实】`apps/prompts/views.py:483`、`debug_services.py:238`、`text2image_stage.py:613` | `requests.get(用户传入的 URL)`，无内网/域名白名单 | SSRF：可探测内网、云元数据 `169.254.169.254` |
| 16 | 【已核实】`core/ai_client/openai_client.py:129` | 流式 `timeout` 默认 **3000** 秒（非流式是 60，:48） | 疑似笔误（3000s = 50 分钟）；连接挂死时长时间不释放 |
| 17 | `apps/workflows/serializers.py:515-561` | `@transaction.atomic` 内直接 `task.delay()` | worker 可能在事务提交前执行 `mark_run_running` → `DoesNotExist` → 节点永久 pending。应改 `transaction.on_commit` |
| 18 | `apps/agent/services/session_manager.py:30-76` | `get → 改 → set` 非原子（存 Redis） | 并发 `append_message`/`update_session` 互相覆盖，消息丢失 |
| 19 | `apps/projects/serializers.py:145-330`、`views.py:861-1079` | 循环内逐分镜 `filter()` 查 5 张表 | 典型 N+1，分镜多时接口超时。应 `storyboard_id__in` 批量取 |
| 20 | `apps/workflows/views.py:98-130` | SSE 每轮全量重查 + 内存 `seen` 去重 | 事件多时 O(n²)；且未按 run 隔离 |
| 21 | `apps/projects/views.py:1132`、`tasks.py:191,383` | 多入口可把同一 `ProjectStage` 置 processing 并投递，无 `select_for_update` | 重复生成、状态互相覆盖 |
| 22 | `apps/ai_proxy/views.py:118-137` | 指定 `model` 未命中时静默回退到该类型第一个 provider | 用户以为用 A 实际用 B，排查困难 |
| 23 | `apps/ai_proxy/views.py:252,399,510`、`models/services.py:377` | `str(exc)` / 上游 `response.text` 原样返回前端 | 泄露内部实现与上游错误详情 |
| 24 | `apps/models/services.py:688-692` | 同步 `_test_llm_provider` 在 async 函数内直调 | 阻塞事件循环 |
| 25 | `apps/models/services.py:807` | `tokens_used` 恒为 0 | 用量统计/计费失真 |
| 26 | `apps/content/processors/image2video_stage.py:428` | `storyboard.get("url", "")` 键不存在恒为 `''`（代码里自注 `## todo bug`） | 死代码 |
| 27 | `apps/content/processors/text2image_stage.py:103`、`image2video_stage.py:113` | `process()` 是 `pass` | 违反 `StageProcessor` 契约，非流式调用 NPE |
| 28 | `apps/projects/views.py:303,502,651,795,957,1344` | 6 处 `except Exception: pass` | 静默吞异常，掩盖真实错误 |
| 29 | `apps/prompts/views.py:313-326` | `validate` 永远 `return valid: True`，未做校验 | 误导调用方 |
| 30 | `apps/prompts/views.py:227-250` | `perform_create` 遇重复 `(set, stage)` 静默 `delete()` 旧模板 | 历史数据静默丢失 |
| 31 | `apps/agent/services/gateway.py:46-49,471-476` | 每次调用新建 `requests.Session()` 不复用；静默吞 `ReadTimeout` 使流无结束事件 | 连接泄漏 + 前端流永不结束 |
| 32 | `apps/projects/models.py:23,100,309` | `Series.user`/`Project.user`/`EpisodeTaskQueue.created_by` 均 `CASCADE` | 删用户级联清空全部作品数据 |
| 33 | `apps/workflows/models.py` + `views.py:180-181` | `WorkflowCanvas.created_by=SET_NULL`，但列表按 `created_by=user` 过滤 | 创建者注销后画布变孤儿、不可见 |
| 34 | `core/ai_client/comfyui_client.py:72-96` | `_prepare_workflow` 只 `json.loads`，docstring 声称注入的 `width/height/steps/seed` 全被忽略 | 参数静默失效 |
| 35 | `core/ai_client/base.py:112` + `openai_client.py:21` | 基类 `await self._generate_text(...)`，但子类是同步 `def` | 契约不统一，一旦被调用直接 `TypeError` |
| 36 | `core/ai_client/mock_llm_client.py:108,164` | async 函数内用 `time.sleep()` | 阻塞事件循环 |
| 37 | `core/pipeline/orchestrator.py:100-115` | `max_retries=0` 时循环不执行，`return result` 未定义 | `NameError` |
| 38 | `config/celery_app.py:38` vs `apps/projects/tasks.py:1112` | `result_expires=3600` 但存在 `time_limit=4200` 的任务 | 结果在任务结束前过期 |
| 39 | `start_services.sh:79,106` | celery 未加 `&` 阻塞后续脚本；只监听 `-Q llm,image,video` 但 `task_routes` 被注释掉（任务实际投默认队列） | 启动脚本实际跑不通；worker 消费不到任务 |
| 40 | `core/services/multi_grid_image_service.py:30`、`core/ai_client/image2video_client.py:120` | `STORAGE_ROOT/'image'/relative_path` 未 `resolve()` | 路径穿越 |

### 前端（React 画布）

| # | 位置 | 问题 |
|---|---|---|
| 41 | 【已核实】`src/store/context/AppContext.jsx:84-103` | UNDO/REDO 用 `{...state, ...prevState}` 展开**整份快照**，会把 `theme`/`performanceMode`/`apiConfigs` 一起回滚；快照缺字段则被清空 |
| 42 | 【已核实】`src/hooks/useHistory.js:37-60` | 在 `setCurrentIndex` 的 updater 内部调用 `setHistory`（副作用）；且 `newIndex` 在嵌套 updater 执行前就被返回，索引很可能不递增。StrictMode 下重复执行会错位。**该 Hook 目前无人调用（死代码）** |
| 43 | 【已核实】`src/components/canvas/FlowCanvas.jsx:1283-1307` | 自动保存 effect 卸载时只 `clearTimeout` 不 flush，700ms 窗口内的编辑**永久丢失**（viewport 有 pagehide flush，图数据没有） |
| 44 | 【已核实】`src/components/canvas/FlowCanvas.jsx:834-847` | `skipAutosaveRef` 是全局布尔，只消费一次；期间若用户真实编辑，该次自动保存被误吞 → 丢数据 |
| 45 | `src/components/canvas/FlowCanvas.jsx:775-831` | 在 `setNodesState` 的 updater 内写 localStorage、改 `nodesRef`；StrictMode 双调用会重复写盘 |
| 46 | 【已核实】`src/components/canvas/FlowCanvas.jsx:3421-3440` + `src/utils/canvas.js:178` | `isValidConnection`（自连/重复校验）**已实现但从未被调用**，`onConnect` 直接 `addEdge` → 可产生自连与重复边 |
| 47 | `src/components/canvas/FlowCanvas.jsx:4585-4601` | `deleteSelectedNodes` 直接 filter 删除，未走 `removeNodesFromGraph`；删除 group 时子节点变孤儿 |
| 48 | `src/services/api.js:46-58` | 401 重试后 `clearTimeout` 位置不对，且重试复用同一 controller | 超时定时器泄漏 |
| 49 | 【已核实】`src/hooks/useLocalStorage.js:20-29` | `setValue` 非稳定引用 → `AppContext.jsx:145` 的自动保存 effect 每次渲染重建，debounce 定时器不断重置 | 高频渲染下 localStorage 可能长期不落盘 |
| 50 | `src/services/workflowRunStreamService.js:63-88`、`agentService.js:121-138` | reader 未在 `finally` 中 `cancel()` | SSE 连接不回收 |
| 51 | 【已核实】`src/store/context/AppContext.jsx`、`ChatContext.jsx`、`useApp.js`、`useChat.js` | 全项目**无消费者**（App.jsx 挂了 Provider 但无人 use） | 死代码 |

### 前端（Vue2 旧后台）

| # | 位置 | 问题 |
|---|---|---|
| 52 | `src/services/message.js:51-54` | `innerHTML` 拼接未转义的后端消息 | XSS |
| 53 | `src/services/apiClient.js:6-9` | `showMessage` 只 `console[type]`，`TODO: 实现全局 Toast` 从未落地 | 全站错误对用户静默 |
| 54 | `src/services/sseService.js:227,241` | SSE URL 不带鉴权信息（其他流式 URL 都追加了 token） | 鉴权接口 401，pipeline SSE 连不上 |
| 55 | `src/components/prompts/PromptTemplateForm.vue:619,1074-1078` | `errors` 新增键未用 `this.$set` | Vue2 侦测不到，字段级校验错误不渲染 |
| 56 | `src/store/modules/assistant.js:226,234` | `currentContext.scopeKey` 无空值保护；`AbortController` 在 `await` 之后才创建 | TypeError + 快速切换 scope 时旧响应回写新会话 |
| 57 | `src/store/modules/prompts.js:469-478` | 创建版本后把"版本"当成新模板 unshift 进列表 | 列表数据被污染 |
| 58 | `src/views/projects/ProjectDetail.vue:314` vs `src/components/projects/StageContent.vue:363` | 一个判 `'processing'`，一个判 `'running'` | 至少一个与后端不符，loading/重连判断失效 |
| 59 | `src/services/sseService.js:91,111-113` | 重连 `setTimeout` 句柄未在 `disconnect()` 清理 | 组件销毁后仍触发一次重连（幽灵连接） |
| 60 | `src/views/projects/ProjectList.vue` | 拿到 `pagination.total` 但无翻页控件 | 大列表永远只显示第一页 |
| 61 | `src/services/apiClient.js:14` | `timeout: 3000000`（50 分钟） | 魔法数 + 请求可能长时间挂死 |

---

## 四、轻微 / 可维护性

- **超长文件**：`FlowCanvas.jsx` **5222 行**、`ProjectCanvas.vue` 3394 行、`views.py`(projects) 2211 行、`ModelCreate.vue` 1894 行、`tasks.py` 1360 行。建议按职责拆 hook / 混入。
- **大段复制粘贴**：
  - `core/ai_client/text2image_client.py:54-155` 与 `core/utils/image_result_utils.py:25-146` 近乎逐行重复。
  - `apps/content/processors/text2image_stage.py` 与 `apps/prompts/debug_services.py` 的 `_guess_image_mime_type` / `_read_image_asset_bytes` / `_render_template_recursively` 重复。
  - `apps/projects/views.py:1603-1639`(resume) 与 `:2056-2094`(run_pipeline) 高度重复。
- **魔法数字/硬编码**：
  - `config/settings/development.py:37` `JIANYING_DRAFT_FOLDER = "D:\JianyingPro Drafts"`（Windows 路径写死）。
  - `core/ai_client/comfyui_client.py:418,576` 硬编码 `http://127.0.0.1:8010`。
  - `apps/content/processors/llm_stage.py:621` storyboard 用 `40960`（疑似应为 4096）。
  - `FlowCanvas.jsx:1642-1643, 2782, 4481` 散落的偏移量常量。
- **死代码**：
  - `core/utils/jianying copy.py`（文件名带空格）、`core/utils/jianying.py`（模块级即执行的脚本，被 import 就跑剪映流程并依赖 `D:\`）。
  - `core/ai_client/factory.py:10` 导入 `validate_executor_for_provider` 从未使用。
  - `base.py:162` `BROKER_URL` 与 `CELERY_BROKER_URL` 重复定义。
  - `apps/agent/services/gateway.py:54` `_build_system_prompt` 已停用但保留。
  - `src/utils/canvas.js` 的 `generateId`/`deepClone`/`getNodesInSelection` 无人使用。
- **调试残留**：`config/celery_app.py:74-88` 三个 signal 用 `print`；`apps/content/processors/llm_stage.py:189` `print(chunk['content'])`；`apps/projects/tasks.py:1149` 遗留 `print`；Vue2 `ProjectDetail.vue` 53 处 console。
- **v-for key 用 index**：`ai_story/frontend/src/views/Layout.vue:57-58`、`ProjectStageSSE.vue:154`；React 侧 `ChatPanel.jsx:446`、`UserSettingsModal.jsx:644`。
- **类型/签名不符**：`core/redis/subscriber.py:108` 标注 `AsyncGenerator` 实为同步生成器；`core/ai_client/registry.py:12` 标 `Optional` 但失败即抛异常。
- **其他**：`config/urls.py:12-16` 用猴子补丁覆盖 `admin.site.has_permission` 且要求 `is_superuser`（绕过 `is_staff`）；`core/utils/file_storage.py:100-116` 的"检查存在→返回路径"存在 TOCTOU；`core/utils/file_storage.py:79` 用 `datetime.now()` 而项目 `USE_TZ=True`；`core/utils/image_downloader.py:104` 日志乱码"图片下��成功"；`apps/projects/serializers.py:825-827` choices 重复 `'asset_extraction'`；`apps/projects/utils.py:100-112` 函数体异常缩进（8 空格）；`start_services.sh:112` 调用不存在的 `test_celery_redis.py`。

**写得好的地方**：`core/redis/publisher.py` / `subscriber.py` 职责单一、结构清晰；`core/pipeline/base.py` 抽象合理；`core/utils/file_storage.py` 日期分层与去重逻辑完整；React 侧节点组件（Image/Video/Audio/Text/DynamicSchema）均已 `memo` 包裹，渲染性能整体可控；Vuex 各 module 均 `namespaced: true`，未发现绕过 mutation 直接改 state。

---

## 五、建议修复顺序

| 优先级 | 事项 | 理由 |
|---|---|---|
| P0 | #1 回调越权、#2 API Key 泄露、#11 SECRET_KEY 兜底、#9 生产 CORS/HOSTS | 安全，可被直接利用 |
| P0 | #3 `retry_stage` 卡死、#7 状态恒成功、#8 失败不落库、#5 await 同步函数 | 功能实际是坏的，用户可感知 |
| P1 | #10 Celery/Web settings 不一致、#17 事务内投递任务、#13 token 进 URL | 难排查的数据不一致 |
| P1 | #18 会话竞态、#43/#44 前端丢数据、#46 未接连线校验 | 用户数据丢失 |
| P2 | #19/#20 N+1 与 SSE 全量重查、#41/#42 撤销重做 | 性能与体验 |
| P3 | 第四节全部 | 可维护性，可随手清理 |

---

## 六、附：按模块索引

| 模块 | 涉及条目 |
|---|---|
| `config/` | 9, 10, 11, 38, 39 |
| `core/` | 16, 34, 35, 36, 37, 40, 4节若干 |
| `apps/workflows` | 1, 17, 20, 33 |
| `apps/projects` | 3, 4, 19, 21, 28 |
| `apps/models` | 2, 24, 25 |
| `apps/prompts` | 5, 6, 15, 29, 30 |
| `apps/content` | 7, 8, 14, 26, 27 |
| `apps/ai_proxy` | 12, 22, 23 |
| `apps/agent` | 18, 31 |
| `linknow/tapnow-studio` | 13, 41-51 |
| `ai_story/frontend` | 52-61 |
