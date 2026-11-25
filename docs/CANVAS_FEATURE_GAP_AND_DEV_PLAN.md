# 画布产品功能差距分析与开发计划

> 对照对象：《产品功能需求清单》（用户中心 / 工作台画布 / 右侧问答智能体 / 项目库 / 左侧功能栏 / 图层，共 36 个功能点）
> 分析范围：`ai_story` 主产品（Django 后端 + 其服务的画布前端）
> 分析时间：2026-10-13
> 判定口径：每条结论均以代码证据为准，不采信 README 自述

---

## 0. 结论摘要（先看这里）

| 判定 | 数量 | 占比 |
| :--- | ---: | ---: |
| ✅ 已满足 | 5 | 14% |
| ⚠️ 部分满足（有骨架，缺关键能力） | 14 | 39% |
| ❌ 未满足 | 17 | 47% |

**三句话总结：**

1. **"画布 + 节点 + AI 生成 + 智能体"这条主线已经相当扎实**——React Flow v12 节点画布、拖拽连线、节点内容编辑、撤销重做、SSE 流式 AI 对话、图像/视频生成代理都真实可用，工程化程度（性能埋点、签名去重、断边、分组、模板展开）不低。
2. **"SaaS 商业闭环"整块是空的**——多租户（主/子账号）、积分计费、充值支付、经销商推广，全部未实现；其中 **积分计费（`apps/billing`）源码已丢失，只剩 `.pyc` 字节码**，属于必须优先处置的遗留问题。
3. **"无限画布绘图工具"这一层几乎为零**——左侧工具箱（选择/平移/矩形/文字/画笔）、图层面板、旋转/锁定、标尺、多人实时协作全部未实现，且 `components/features/*`、`store/reducers`、`styles` 三个目录为空，印证"规划了但没做"。

---

## 1. 重要前提：功能清单的归属与项目真实形态

这一点必须先讲清楚，否则后面的判定会全部错位。

**功能清单描述的是一个"无限画布工作台 + SaaS 多租户协作平台"**（Figma/白板形态 + 节点式 AI 工作流 + 商业闭环）。它**不是** `ai_story/frontend` 这个 Vue2 管理后台的形态。

实际代码分布是这样的：

| 层次 | 位置 | 技术栈 | 角色 |
| :--- | :--- | :--- | :--- |
| **画布前端** | `linknow/tapnow-studio/` | React 19 + `@xyflow/react` v12 + Context/useReducer | 功能清单真正对应的"工作台" |
| **后端 API** | `ai_story/backend/` | Django + DRF + Celery + Redis | 为画布前端提供全部接口 |
| **旧管理前端** | `ai_story/frontend/` | Vue2 + Webpack | 分集/剧本/提示词/模型管理后台，**与本次功能清单基本无关** |

**决定性证据**（说明 linknow 才是功能清单的主角）：

- `linknow/tapnow-studio/src/constants/apiConfig.js` 调用的全部是 ai_story 的接口前缀：`/api/v1/workflows/canvases/`、`/api/v1/agent/session/init/`、`/api/v1/ai/images/generations`……
- `apps/agent/services/context_builder.py` 里存在 `linknow:` 作用域分支，说明智能体服务专为 linknow 画布设计
- `apps/users/serializers.py` 注册校验读取的是 `LINKNOW_REGISTRATION_INVITE_CODE`（`config/settings/base.py`），即 **ai_story 的注册接口就是给 linknow 用的**
- `apps/workflows`（画布/节点/边/运行）与 `apps/billing`（积分授权 `CreditAuthorization.reference_type = workflow_node_run`）的建模，全部围绕画布工作流

> **因此本文档的判定口径为**：画布前端以 `linknow/tapnow-studio` 为准，接口能力以 `ai_story/backend` 为准，`ai_story/frontend`（Vue 后台）不纳入功能清单对照。

---

## 2. 逐模块功能对照

### 一、用户中心

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 1 | 登录（手机号/密码、验证码） | ❌ | `apps/users/serializers.py:17-36` 仅 `username`+`password`；全库无 `phone`/`sms`/`captcha` 匹配。前端 `LoginForm.jsx` 同为用户名密码 |
| 2 | 注册 | ⚠️ | 有（`RegisterView`），但**强制邀请码**且为**全局单码**（`serializers.py:61-65`，`LINKNOW_REGISTRATION_INVITE_CODE`，默认 `charles`），非"每用户邀请码" |
| 3 | 忘记密码 | ❌ | 全库无 `forgot`/`reset_password` 匹配；仅有需登录且校验旧密码的 `ChangePasswordView`（`views.py:134`） |
| 4 | 跳转画布工作区（按角色查权限范围） | ❌ | 无主/子账号概念。全库 `parent`/`sub_account`/`主体` 命中均为误报（路径 `.parent`、节点 `$parent` 引用、图像提示词文本） |
| 5 | 个人信息（头像/昵称/角色/积分展示） | ❌ | 使用 **Django 内置 User**（`users/models.py` 仅 `UserPreference`），`auth_user` 表**无 phone/avatar/nickname/role/credits 字段**；`UserSerializer` 只返回 `username/email/first_name/last_name/is_superuser/date_joined` |
| 6 | 头像上传（压缩/格式校验/云存储） | ❌ | 无 `avatar` 匹配；前端 `Sidebar.jsx:62-64` 用用户名首字母生成色块 |
| 7 | 子账号管理（列表/增删/共享项目与积分） | ❌ | 不存在 |
| 8 | 充值积分（套餐/订单/支付/回调） | ❌ | 不存在。无套餐、无订单、无 `wechatpay`/`alipay`/`payment` 匹配 |
| 9 | 联系我们 / 经销商推广 / 邀请码体系 / 二维码 | ❌ | 无 `distributor`/`referral`/`推广`/`qrcode`/`联系我们` 匹配。仅注册时的一次性邀请码校验 |
| 10 | 进入与初始化（默认 1:1、视口居中、图层面板收起、工具栏左侧固定） | ⚠️ | 视口持久化有（`canvasStorage.js` + `updateCanvas({viewport})`），但**无图层面板、无左侧工具栏**，"初始化状态"无对应实现对象 |

### 二、工作台（画布核心操作）

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 11 | 协同工作（同主体子账号同步画布 + 在线成员数） | ❌ | 无子账号体系，无 presence，无成员数展示 |
| 12 | 平移（空格+拖动 / 平移工具） | ⚠️ | 有平移（`panOnDrag={[1,2]}` 中/右键，`FlowCanvas.jsx:5097`），但**无空格键拖动、无平移工具按钮** |
| 13 | 缩放（0.2x–3x，以鼠标点为中心，缩小简化渲染） | ⚠️ | 有滚轮中心缩放，但范围是 **0.03–2**（`canvasConfig.js:102-103`），非 0.2–3；无"缩小自动简化线条/文本"逻辑 |
| 14 | 元素操作（8 控制点/拖动/缩放/旋转/Ctrl 多选/Shift 框选/右键菜单/图层操作） | ⚠️ | **有**：选中+`NodeResizer` 控制点、多选（`multiSelectionKeyCode="Shift"`）、框选（`selectionOnDrag`+`SelectionMode.Partial`）、右键菜单（复制/删除/添加资产/分组，`FlowCanvas.jsx:4894-4978`）。**缺**：旋转、锁定、图层面板操作 |
| 15 | 自动保存（30s 本地 + 操作结束增量同步 + 断网缓存合并） | ⚠️ | 有**防抖 700ms 全量存云端 + JSON 签名去重**（`FlowCanvas.jsx:1283-1307`）。**缺**：30s 本地定时保存、字段级增量、断网队列与合并 |
| 16 | 撤销/重做（最多 200 步） | ⚠️ | 有（`FlowCanvas.jsx:397-399,3178-3196`，`Ctrl+Z`/`Ctrl+Shift+Z`），但上限 **50 步**；`hooks/useHistory.js` 是未被引用的死代码 |
| 17 | 性能优化（视口渲染、非视口不渲染不触发事件、按需加载卸载） | ⚠️ | React Flow 自带视口裁剪，另有 `canvasPerf.js` 性能埋点与 `refreshGraphRuntime` 增量重算（`FlowCanvas.jsx:682-755`）；**无显式的"按需加载/卸载元素"** |
| 18 | 多人实时协作（WebSocket 全双工：光标/选中/移动/缩放/编辑/删除同步） | ❌ | **不存在**。`config/asgi.py` 仅 `get_asgi_application()`，无 `ProtocolTypeRouter`/`URLRouter`；`INSTALLED_APPS` 无 `channels`；无 `consumers.py`/`routing.py`；无 `CHANNEL_LAYERS`；前端无 `socket.io-client`。现有"实时"仅**单向 SSE**（生成进度），非协作 |
| 19 | 光标追踪 + 工作流连线（角色节点连接多个视频模块、工作流可复制） | ⚠️ | 无光标追踪；但"节点连线 + 分组 + 工作流模板展开/复制"有基础（`templateMaterialization.js`、`duplicateNode`、`GroupNode`） |

### 三、右侧问答智能体

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 20 | 对话框 + 欢迎语（后台配置欢迎语） | ✅ | `ChatPanel.jsx` 头部"AI 对话"，空状态引导语（`ChatPanel.jsx:5-9,430-442`）。欢迎语为前端硬编码，**未走后台配置接口** |
| 21 | 对话交互（多轮/上下文/意图识别/语气适配/快捷回复/流式） | ✅ | 多轮+上下文（`session_manager.py`，`context_builder.py` 按 scope 注入 Project/Stage/分镜）、意图识别（`gateway.py:15` 解析 `agent-ui` fenced block）、流式（`AgentSessionStreamView` SSE 逐 token）、快捷回复（`EMPTY_PROMPTS`）。**语气适配**未见显式实现 |
| 22 | 剧本问答与解析（剧情/人物关系/逻辑校验/优化建议） | ⚠️ | 无专用剧本问答逻辑；依赖通用对话 + `screenplays` 数据。缺**结构化的剧本解析/逻辑校验**能力 |
| 23 | 创意生成与灵感拓展（故事创意/角色名/标题/风格化） | ⚠️ | 通用对话可覆盖，但无专项 prompt 模板与快捷入口 |
| 24 | 上传文件（PDF/JPG/PNG/DOCX/DOC/XLS/XLSX/WPS，≤200MB） | ❌ | 智能体**无附件入口**（`ChatPanel.jsx` 无 `type="file"`）。后端 `FileUploadView`（`ai_proxy/views.py:515-561`）**无格式白名单、无大小限制**，且只区分 image/其余，**不支持 PDF/DOCX/XLS 解析** |
| 25 | 输入框（多行/最大字数/回车发送/发送后清空） | ✅ | `ChatPanel.jsx` 文本域，回车发送，发送后清空 |
| 26 | 历史记录（自动保存问题/回答/时间戳/项目归属，条数后台配置，分页，点击回填，倒序） | ⚠️ | **仅存 Redis cache**：`apps/agent` **无 models.py**，会话 key `agent_session:{user_id}:{scope_key}`，**仅保留最近 20 条**、**24h 过期**、**无项目归属字段**；前端无历史会话列表 UI（`ChatContext` 有 sessions 概念但未接入） |

### 四、项目库

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 27 | 项目库（列表/名称/创建时间/封面缩略图/搜索/排序/筛选/进入/删除软删） | ⚠️ | "我的工作流"面板（`LeftPanel.jsx`）：有列表、名称、时间（`ordering=-updated_at`）、进入、删除二次确认。**缺**：封面缩略图、搜索、排序切换、筛选；后端 `WorkflowCanvas` **无软删除字段**（无 `deleted_at`/`is_deleted`），删除为硬删 |
| 28 | 新建项目（新标签页/空白画布/自动保存） | ✅ | `handleCreateWorkflow`（`LeftPanel.jsx:295-312`）+ 自动保存链路 |
| 29 | 删除项目（二次确认 + 删除后跳转项目库） | ⚠️ | 有二次确认（`ConfirmPopover`），但为硬删除、无"删除后跳转项目库"的显式流程 |

### 五、左侧功能栏

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 30 | 光标选择（切换选择态 + 框选） | ❌ | `App.jsx:37` 有 `activeTool='select'` 残留状态，但**无任何工具切换 UI** |
| 31 | 平移工具（抓手模式） | ❌ | 无工具栏平移按钮，仅 React Flow 内置中/右键平移 |
| 32 | 新增（图片上传/视频上传，进度条，首帧显示，可播放） | ⚠️ | 图片/视频上传**在节点内部**（`ImageNode.jsx:795-802`、`VideoNode.jsx:809-811`），非工具栏工具；**无上传进度条、无首帧抽帧**（`onUploadProgress` 无匹配） |
| 33 | 形状（矩形绘制，填充/边框/透明度） | ❌ | 无矩形绘制工具；`utils/canvas.js` 仅有 `isPointInRect` 等几何工具函数 |
| 34 | 文字（画布任意位置单击创建，字体/字号/颜色/对齐/粗斜体） | ⚠️ | 有 `TextNode`（通过"添加节点"创建），但**非"画布单击任意位置创建"**，样式能力有限 |
| 35 | 画笔（自由手绘标记/画圈/划线/涂鸦） | ❌ | 全库 `brush`/`画笔`/`freehand`/`pencil` 无匹配 |
| 36 | 素材（人物角色/虚拟数字人/动物/道具/场景风格/固定 IP 形象） | ⚠️ | 有 `GlobalVariable`（`apps/prompts/models.py:130`，`variable_type` 含 image，支持 `group` 分组）+ `ProjectAssetBinding`（`apps/projects/models.py:335`）+ "我的资产"面板（可拖拽素材入画布）。**缺**：角色形象/声音/性格/动作习惯的建模（**无"主体素材"专用模型**） |
| 37 | 图像生成器（提示词/模型选择/参考图/分辨率 512-4K/比例/积分消耗/按钮置灰） | ⚠️ | 有 `ImageNode` + 后端 `ImagesGenerationsProxyView`（支持 `size`/`width`/`height`/`aspect_ratio`/`ratio`/参考图 `image(s)`/`mask`/`strength`/`n`/`seed`）。**缺**：节点内**模型选择器**、**分辨率档位 UI**、**比例选择器**、**积分消耗显示与按钮置灰** |
| 38 | 视频生成器（提示词/模型选择/首尾帧/参考主体/视角/分辨率/时长 3-15s/比例/积分） | ⚠️ | 有 `VideoNode` + 后端 `VideosGenerationsProxyView`（`duration_seconds`/`aspect_ratio`/`resolution`/`images`/`negative_prompt`/`generate_audio`/`camera_movement_description`）。**缺**：**首帧/尾帧**（全库无 `first_frame`/`last_frame`）、**参考主体**、**视角**（仅运镜描述，无 `viewpoint`/`camera_angle` 参数）、模型选择器、积分 |

### 六、左下角图层

| # | 功能点 | 判定 | 证据与缺口 |
| :-- | :--- | :---: | :--- |
| 39 | 图层面板（元素列表/类型图标/按层级排序/单击定位选中/编辑/显隐/锁定/删除/上下移层级/拖拽排序/实时同步） | ❌ | **完全不存在**。全库 `layer`/`图层`/`zIndex`/`锁定`/`层级` 命中均为无关项（节点内菜单 CSS、Tooltip 显隐）。唯一"层级"概念是 `GroupNode` 分组容器，无元素列表与图层管理 |

---

## 3. 缺口汇总（按性质归类）

**A. 商业闭环缺失（最严重）**
- 多租户：主/子账号、权限范围、项目共享 — 0%
- 积分计费：账户/流水/扣减/挂钩生成链路 — 0%（且**源码已丢失**）
- 充值支付：套餐/订单/微信支付宝/回调 — 0%
- 经销商推广：邀请码体系/推广关系/二维码/联系我们 — 0%

**B. 画布编辑器能力缺失**
- 左侧工具箱（选择/平移/矩形/文字/画笔）— 0%
- 图层面板 — 0%
- 旋转、锁定 — 0%
- 标尺 — 0%
- 撤销上限 50 → 200；自动保存三层机制 — 部分

**C. 实时协作缺失**
- WebSocket 通道、光标/选中/成员 presence — 0%

**D. AI 能力缺口**
- 聊天文件上传与文档解析 — 0%
- 智能体历史持久化（DB + 列表 UI + 条数配置）— 仅 cache
- 首帧/尾帧、参考主体、视角、模型选择器、积分提示 — 0%
- 剧本问答/创意生成专项能力 — 未专门化

**E. 遗留风险**
- `apps/billing` 仅剩 `.pyc`，未注册到 `INSTALLED_APPS`/`urls`；数据库仍残留 `credit_accounts` 等表与迁移记录 — **需优先决策**

---

## 4. 开发计划

> 排序原则：先解锁商业模式与架构风险，再补编辑器体验，最后做运营增强。
> 每项含：改造点 / 依赖 / 验收标准。

### P0 — 架构与商业闭环（决定项目能否商用）

#### P0-1 处置 billing 遗留（决策项，0.5 天）
- **改造点**：二选一 —— ① 用 `pycdc` 反编译 `.pyc` 恢复源码后校验；② 直接按现有数据库表结构（`credit_accounts`/`credit_authorizations`/`credit_ledger_entries`）重写 `models.py`/`services.py`。恢复后加入 `INSTALLED_APPS` 与 `config/urls.py`，并编写迁移对齐。
- **依赖**：无（阻塞 P0-2/P0-3）
- **验收**：`manage.py check` 通过；`/api/v1/billing/account/`、`/authorizations/`、`/ledger/` 可访问；迁移与现有表结构一致。

#### P0-2 用户体系扩展（自定义 User + 手机号 + 忘记密码）
- **改造点**：新建 `apps/accounts`（或改造 `users`）引入自定义 User（`phone`/`avatar`/`nickname`/`role`/`parent`）；手机号验证码（短信服务商接入 + Redis 存码）；忘记密码/重置密码接口；头像上传（压缩 + 格式校验 + 复用 `DateBasedFileStorage`）。**注意**：更换 User 模型需在项目早期完成，涉及全库迁移。
- **依赖**：无
- **验收**：手机号验证码登录/注册/重置密码全链路可跑；`profile` 返回头像/昵称/角色；头像上传后返回可访问 URL。

#### P0-3 积分计费接入生成链路
- **改造点**：在 `apps/ai_proxy`（images/videos/chat）与 `apps/workflows/node_executors/*` 注入 `BillingService.hold_credits`/`commit`/`release`；前端在图像/视频生成器上展示消耗积分并做"积分不足置灰"；生成失败自动返还。
- **依赖**：P0-1、P0-2
- **验收**：生成一次图像/视频后 `credit_accounts.available_credits` 正确扣减、`credit_ledger_entries` 有流水；失败任务积分自动回滚；余额不足时接口返回明确错误码且前端置灰。

#### P0-4 充值积分与支付
- **改造点**：套餐配置模型 + 订单模型 + 微信/支付宝下单与回调 + 到账幂等 + 超时回滚 + 重新发起支付。
- **依赖**：P0-3
- **验收**：沙箱环境完成"选套餐 → 生成订单 → 扫码支付 → 回调到账 → 余额更新"闭环；重复回调不重复加积分。

#### P0-5 主/子账号多租户
- **改造点**：`parent` 关系 + 权限范围（主账号可见全部子账号画布；子账号仅自身+授权）；项目/积分共享；前端角色化路由与列表过滤（`WorkflowCanvas` 查询按主体过滤）。
- **依赖**：P0-2
- **验收**：主账号登录可见全量画布；子账号仅见自身与授权画布；子账号不展示积分总额。

#### P0-6 多人实时协作（WebSocket）
- **改造点**：后端引入 `channels` + `channels_redis` + `CHANNEL_LAYERS` + `ProtocolTypeRouter` 改造 `config/asgi.py` + 画布 consumer（`canvas:{id}` 房间）；广播光标/选中/节点增删改/边变更；presence 维护在线成员；前端接入 WS 客户端并做"x 位成员协作中"展示与远端光标渲染；`WorkflowCanvas` 增加乐观锁/版本号防冲突。
- **依赖**：P0-5（需按主体隔离房间）
- **验收**：两个浏览器同时打开同一画布，光标/选中/节点拖动实时同步；断开重连后状态一致；成员数正确增减。

### P1 — 画布编辑器体验补齐

#### P1-1 左侧工具栏（选择/平移/矩形/文字/画笔）
- **改造点**：`Sidebar.jsx` 增加"工具组"分区；新增 `RectTool`/`FreehandTool`（建议用 SVG overlay 或轻量 canvas 层）、`TextTool`（画布单击创建）、选择/平移模式切换（React Flow `panOnDrag`/`selectionOnDrag` 动态切换 + 空格键平移）。
- **依赖**：无
- **验收**：五类工具可切换且行为符合清单；画笔笔迹可撤销；矩形可设填充/边框/透明度。

#### P1-2 图层面板
- **改造点**：新增 `LayerPanel`（左下角），从画布 `nodes`/`edges` 派生元素列表（含类型图标、层级顺序）；实现单击定位选中、显隐、锁定、删除、上移/下移层级、拖拽排序；与画布双向实时同步。
- **依赖**：P1-1（工具栏改动共用布局）
- **验收**：面板与画布增删改双向同步；拖拽排序后画布渲染层级同步变化；锁定后元素不可选中/移动。

#### P1-3 元素操作补齐（旋转 + 锁定）
- **改造点**：节点旋转手柄（`rotation` 存节点 data/style）+ 锁定态（`draggable=false`/`selectable=false`）；右键菜单增加"锁定/解锁""旋转"。
- **依赖**：P1-2
- **验收**：节点可旋转并持久化；锁定节点无法拖动/选中，图层面板可解锁。

#### P1-4 撤销/重做提升至 200 步 + 自动保存三层机制
- **改造点**：`maxHistorySize` 50→200 并清理 `hooks/useHistory.js` 死代码或统一复用之；新增 30s 定时本地保存（localStorage/IndexedDB 快照）；实现字段级增量同步（diff 提交）；新增 `navigator.onLine` 监听 + 断网操作队列 + 联网合并上传。
- **依赖**：无
- **验收**：连续 200 步操作可完整撤销；断网下编辑不丢失，联网后自动合并且无覆盖冲突。

#### P1-5 图像/视频生成器面板补齐
- **改造点**：节点内增加**模型选择器**（对接 `/api/v1/ai/models`）、**分辨率档位**（512/1K/2K/4K，按模型动态）、**比例选择器**、**积分消耗显示 + 余额不足置灰**；视频节点增加**首帧/尾帧**上传（后端 `VideosGenerationsProxyView` 新增 `first_frame`/`last_frame` 参数透传）、**参考主体**下拉（对接主体素材）、**视角**选项（映射为 `camera_movement_description` 或新增参数）；上传进度条 + 视频首帧抽帧显示。
- **依赖**：P0-3（积分）、主体素材模型（P1-6）
- **验收**：切换模型后分辨率/时长/比例选项自适应；提示词为空或积分不足时生成按钮置灰；首尾帧生效且生成结果可控。

#### P1-6 主体素材模型
- **改造点**：新增"主体素材"模型（角色形象/声音/性格/动作习惯/类型：人物/数字人/动物/道具/场景风格/IP），支持复制整条工作流后替换主体信息；扩展 `GlobalVariable` 或新建 `SubjectAsset`。
- **依赖**：无
- **验收**：可创建多类型主体并绑定到生成节点；复制工作流换主体后生成内容一致性与差异符合预期。

#### P1-7 智能体文件上传与文档解析
- **改造点**：`ChatPanel.jsx` 增加附件按钮（格式白名单 PDF/JPG/PNG/DOCX/DOC/XLS/XLSX/WPS，≤200MB，超限提示）；后端 `FileUploadView` 增加白名单 + 大小校验 + 文档解析（PDF/DOCX/XLS）并注入 agent 上下文。
- **依赖**：无
- **验收**：上传合规文件可被智能体读取并回答；超 200MB 或不支持格式给出明确提示。

#### P1-8 智能体历史记录持久化
- **改造点**：`apps/agent` 新增 `models.py`（`AgentSession`/`AgentMessage`，含时间戳、项目归属）；历史写入 DB（保留 cache 做热点）；后台配置显示条数；前端历史会话列表 + 分页 + 点击回填上下文。
- **依赖**：无
- **验收**：会话重启后历史仍在；可按条数配置分页加载；点击历史项恢复上下文。

#### P1-9 项目库补齐
- **改造点**：`WorkflowCanvas` 增加 `deleted_at` 软删除 + 默认过滤；列表增加封面缩略图（画布首帧/首图快照）、搜索、排序切换、筛选；删除后跳转项目库。
- **依赖**：无
- **验收**：软删除后列表不可见但数据可恢复；搜索/排序/筛选生效；封面缩略图正确显示。

### P2 — 运营与体验增强

| 编号 | 事项 | 改造点 | 验收 |
| :-- | :--- | :--- | :--- |
| P2-1 | 经销商推广体系 | 每用户邀请码生成/分享、推广关系绑定（扫码/链接/邀请码三方式）、返利、分销后台 | 三种绑定方式均生效，推广关系可追溯 |
| P2-2 | 联系我们 | 后台配置微信二维码图片地址；前端悬停浮层 | 配置后可展示二维码浮层 |
| P2-3 | 剧本问答/创意生成专项化 | 为 `agent` 增加剧本解析/逻辑校验/优化建议与创意生成的专项 prompt 与快捷入口 | 快捷指令触发专项能力，输出结构化 |
| P2-4 | 语气适配 | agent 支持正式/轻松/创意等多语气切换 | 切换语气后回答风格可感知变化 |
| P2-5 | 标尺 | 画布增加水平/垂直标尺并与视口同步 | 平移缩放时标尺实时同步 |
| P2-6 | 视口性能优化深化 | 按需加载/卸载视口外元素；缩小自动简化线条与小文本 | 大画布（500+ 节点）平移缩放保持流畅 |
| P2-7 | 智能体欢迎语后台配置 | 增加配置接口，前端替换硬编码引导语 | 后台改配置前端生效 |

---

## 5. 关键决策与风险

| 风险 | 说明 | 建议 |
| :--- | :--- | :--- |
| **billing 源码丢失** | `apps/billing` 仅剩 `.pyc`（Python 3.11，反编译工具支持有限），但数据库表与迁移记录仍在 | 优先决策"反编译恢复"还是"按表结构重写"，越早越好，否则积分体系无地基 |
| **更换 User 模型** | 当前用 Django 内置 User，改为自定义 User 属高影响迁移 | 必须在 P0 早期完成，晚做成本指数上升 |
| **多租户改造面广** | 主/子账号会波及所有列表查询与权限 | 与 P0-6 协作房间隔离一并设计 |
| **实时协作技术选型** | 现有 SSE 为单向，协作需双向 | 引入 `channels`+`channels_redis`，与现有 Redis 复用；注意 asgi 部署（已用 daphne） |
| **前端双栈** | 画布前端（React）与旧管理后台（Vue2）并存 | 明确本次只动 React 画布端，Vue 后台不在范围内 |
| **无软删除** | 画布/节点/边均为硬删 | P1-9 统一补软删除，避免误删不可恢复 |

---

## 6. 附：判定依据一览（代码位置速查）

| 主题 | 文件 |
| :--- | :--- |
| 画布主组件（5222 行） | `linknow/tapnow-studio/src/components/canvas/FlowCanvas.jsx` |
| 画布配置（缩放范围/节点类型） | `linknow/tapnow-studio/src/components/canvas/canvasConfig.js` |
| 左侧功能栏 | `linknow/tapnow-studio/src/components/layout/Sidebar.jsx` |
| 项目库/资产面板 | `linknow/tapnow-studio/src/components/layout/LeftPanel.jsx` |
| AI 对话面板 | `linknow/tapnow-studio/src/components/layout/ChatPanel.jsx` |
| 接口常量 | `linknow/tapnow-studio/src/constants/apiConfig.js` |
| 用户认证 | `ai_story/backend/apps/users/{urls,views,serializers,models}.py` |
| 画布数据模型 | `ai_story/backend/apps/workflows/models.py` |
| 画布 API（含整体保存 `graph`） | `ai_story/backend/apps/workflows/{urls,views,serializers}.py` |
| AI 生成代理 | `ai_story/backend/apps/ai_proxy/views.py` |
| 智能体会话（Redis cache） | `ai_story/backend/apps/agent/services/session_manager.py` |
| 智能体流式 | `ai_story/backend/apps/agent/views.py` |
| 积分计费（源码已丢失） | `ai_story/backend/apps/billing/__pycache__/*.pyc` |
| ASGI（无 WS 路由） | `ai_story/backend/config/asgi.py` |
| 设置（无 channels） | `ai_story/backend/config/settings/base.py` |
