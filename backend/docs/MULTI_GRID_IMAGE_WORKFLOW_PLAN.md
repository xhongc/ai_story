# 多宫格图片与图片编辑节点实现方案

## 1. 需求澄清后的正确职责边界

基于最新澄清，功能应拆成两个独立节点，而不是把“多宫格生成”和“切片高清还原”放进同一个阶段。

### 1.1 多宫格图片节点

`multi_grid_image` 节点本身属于文生图能力的一个业务变体，职责是：

- 根据提示词直接生成一张多宫格图片；
- 后台按格子切割为多张独立图片；
- 输出结果是多张切片图片；
- 不在这个节点内执行高清还原。

### 1.2 图片编辑节点

`image_edit` 节点是独立节点，职责是：

- 接收已有图片作为输入；
- 支持单张图编辑、图生图、高清修复；
- 当输入来自多宫格节点时，对切片结果逐张执行高清还原；
- 输出结果是编辑后的高清图片集合。

这意味着：

1. 多宫格节点的模型能力归类仍然是文生图。
2. 图片编辑节点才需要新增“图生图/图片编辑”模型类型。
3. 多宫格节点内部只做“生成 + 切割”，不做“切片重绘/超分”。

---

## 2. 推荐最终命名

### 2.1 模型能力分类

在 `ModelProvider.provider_type` 中新增：

- `image_edit`: 图片编辑 / 图生图模型

保留现有：

- `text2image`: 文生图模型
- `image2video`: 图生视频模型
- `llm`: 文本模型

### 2.2 业务阶段分类

建议新增两个业务阶段：

- `multi_grid_image`: 多宫格图片
- `image_edit`: 图片编辑

说明：

- `multi_grid_image` 是项目流程里的“文生图增强型阶段”。
- `image_edit` 是项目流程里的“图片后处理阶段”。
- 二者是串联关系，不应合并。

### 2.3 阶段与模型能力映射

推荐固定映射如下：

- `rewrite -> llm`
- `storyboard -> llm`
- `image_generation -> text2image`
- `multi_grid_image -> text2image`
- `camera_movement -> llm`
- `video_generation -> image2video`
- `image_edit -> image_edit`

其中最关键的是：

- `multi_grid_image` 走 `text2image`
- `image_edit` 走 `image_edit`

---

## 3. 推荐业务流程

推荐将整条链路拆为两步：

### 步骤 A：多宫格生成

1. 用户在提示词管理中配置 `multi_grid_image` 模板。
2. 用户在项目画布执行多宫格图片节点。
3. 后台调用 `text2image` 模型生成一张多宫格图。
4. 后台按预设网格配置将该图片切割成多个 tile。
5. 节点输出为多个切片图，并保存到项目数据中。

### 步骤 B：图片编辑高清还原

1. 用户在画布执行图片编辑节点。
2. 输入来源可选择：
   - 多宫格节点的全部切片；
   - 多宫格节点的部分切片；
   - 普通文生图节点生成的单图。
3. 后台逐张调用 `image_edit` 模型进行高清还原。
4. 输出高清结果，并供用户选择作为最终成图。

---

## 4. 为什么要这样拆

这样拆分比“多宫格节点直接做高清还原”更合理，原因如下：

### 4.1 语义更清晰

- 多宫格节点解决“生成多张候选图”。
- 图片编辑节点解决“对已有图做高质量后处理”。

### 4.2 与模型能力一致

- 多宫格节点本质还是文生图，不应绑定 `image_edit` 模型。
- 高清修复、局部重绘、图生图增强才属于 `image_edit` 能力。

### 4.3 更利于复用

独立 `image_edit` 节点后，后续可复用于：

- 普通文生图结果高清化；
- 老图翻新；
- 局部改图；
- 扩图。

### 4.4 更利于画布编排

如果后续用户不想对所有切片都做高清，可以：

- 只选 1 张切片送到 `image_edit`；
- 只重绘其中失败或最满意的一张；
- 多宫格节点仍然只承担素材输出角色。

---

## 5. 数据结构设计

## 5.1 模型管理

### `backend/apps/models/models.py`

在 `ModelProvider.PROVIDER_TYPES` 新增：

- `('image_edit', '图片编辑模型')`

新增执行器列表：

- `IMAGE_EDIT_EXECUTORS = [...]`

建议首批支持：

- `core.ai_client.image_edit_client.ImageEditClient`
- `core.ai_client.comfyui_client.ComfyUIClient`
- `core.ai_client.mock_image_edit_client.MockImageEditClient`

同步修改：

- `get_executor_choices`
- `get_default_executor`
- `validate_executor_class`
- serializer 校验
- test connection
- 前端模型管理列表和筛选

---

## 5.2 项目阶段

### `backend/apps/projects/models.py`

在 `ProjectStage.STAGE_TYPES` 中新增：

- `('multi_grid_image', '多宫格图片')`
- `('image_edit', '图片编辑')`

项目初始化时同步自动创建这两个阶段。

---

## 5.3 提示词模板

### `backend/apps/prompts/models.py`

在 `PromptTemplate.STAGE_TYPES` 中新增：

- `('multi_grid_image', '多宫格图片')`
- `('image_edit', '图片编辑')`

同时同步修改：

- 提示词调试会话/运行记录中的阶段枚举；
- 调试工作台阶段标签；
- 阶段到 provider_type 的映射。

---

## 5.4 项目模型配置

### `backend/apps/projects/models.py`

在 `ProjectModelConfig` 中新增两个模型绑定：

- `multi_grid_providers`：仅允许 `text2image`
- `image_edit_providers`：仅允许 `image_edit`

这样每个项目都可以分别选择：

- 哪个文生图模型负责生成多宫格；
- 哪个图片编辑模型负责后续高清还原。

---

## 5.5 新领域模型设计

建议不要让多宫格结果直接混进 `GeneratedImage` 的单一语义里，而是新增独立模型。

### `MultiGridImageTask`

建议新增在 `backend/apps/content/models.py`：

字段建议：

- `id`
- `storyboard`
- `source_prompt`
- `source_image_url`：原始生成出的多宫格大图
- `grid_rows`
- `grid_cols`
- `tile_gap`
- `outer_padding`
- `split_config`
- `status`
- `model_provider`
- `prompt_used`
- `generation_metadata`
- `created_at`
- `updated_at`

### `MultiGridTile`

字段建议：

- `id`
- `task`
- `tile_index`
- `row_index`
- `col_index`
- `crop_box`
- `tile_image_url`
- `status`
- `created_at`
- `updated_at`

说明：

- `MultiGridImageTask` 表示一次多宫格生成任务。
- `MultiGridTile` 表示该任务切出来的每个格子结果。
- 这里先不保存高清还原结果，高清结果应归属图片编辑阶段。

### `EditedImageTask`

为图片编辑节点新增独立任务模型更合理。

字段建议：

- `id`
- `storyboard`
- `source_stage_type`：`multi_grid_image` / `image_generation`
- `source_image_url`
- `status`
- `model_provider`
- `prompt_used`
- `generation_metadata`
- `created_at`
- `updated_at`

### `EditedImageResult`

字段建议：

- `id`
- `task`
- `source_tile_id`：可空，若来源于多宫格切片则关联
- `source_image_url`
- `edited_image_url`
- `status`
- `error_message`
- `generation_params`
- `generation_metadata`
- `created_at`
- `updated_at`

---

## 6. 执行链路设计

## 6.1 多宫格图片阶段

建议新增处理器：

- `backend/apps/content/processors/multi_grid_image_stage.py`

职责：

1. 获取项目、分镜、模板、模型。
2. 调用 `text2image` 模型生成一张多宫格图。
3. 使用图片处理服务对多宫格图执行切割。
4. 保存 `MultiGridImageTask` 和 `MultiGridTile`。
5. 回写 `ProjectStage.output_data`。
6. 推送 SSE 进度。

### 输入结构建议

```json
{
  "storyboard_ids": ["..."],
  "grid_rows": 2,
  "grid_cols": 2,
  "tile_gap": 0,
  "outer_padding": 0,
  "width": 1024,
  "height": 1024,
  "steps": 20,
  "negative_prompt": ""
}
```

### 输出结构建议

```json
{
  "total_tasks": 1,
  "success_count": 1,
  "failed_count": 0,
  "storyboards": [
    {
      "storyboard_id": "...",
      "task_id": "...",
      "source_image_url": "...",
      "grid_rows": 2,
      "grid_cols": 2,
      "tiles": [
        {
          "tile_id": "...",
          "tile_index": 0,
          "tile_image_url": "...",
          "status": "completed"
        }
      ]
    }
  ]
}
```

关键点：

- 输出只到切片图，不包含 `restored_image_url`。

---

## 6.2 图片编辑阶段

建议新增处理器：

- `backend/apps/content/processors/image_edit_stage.py`

职责：

1. 接收一组已有图片。
2. 逐张调用 `image_edit` 模型。
3. 保存编辑结果。
4. 回写阶段输出。

### 输入来源模式

建议支持：

- `source_stage=image_generation`
- `source_stage=multi_grid_image`
- `source_images=[...]`

当 `source_stage=multi_grid_image` 时，可传：

```json
{
  "storyboard_ids": ["..."],
  "source_stage": "multi_grid_image",
  "tile_ids": ["...", "..."],
  "prompt": "提升清晰度，补全细节，保持人物一致性",
  "strength": 0.3,
  "target_width": 1536,
  "target_height": 1536
}
```

### 输出结构建议

```json
{
  "total_inputs": 4,
  "success_count": 4,
  "failed_count": 0,
  "results": [
    {
      "result_id": "...",
      "source_tile_id": "...",
      "source_image_url": "...",
      "edited_image_url": "...",
      "status": "completed"
    }
  ]
}
```

---

## 7. AI 客户端设计

### 7.1 图片编辑客户端

建议在 `backend/core/ai_client/base.py` 新增：

- `ImageEditClient(BaseAIClient)`

推荐接口：

```python
def generate(
    self,
    image_url: str,
    prompt: str = "",
    mask_url: str = "",
    strength: float = 0.35,
    width: int = 1024,
    height: int = 1024,
    **kwargs
) -> AIResponse:
    ...
```

### 7.2 执行器实现

建议新增：

- `backend/core/ai_client/image_edit_client.py`
- `backend/core/ai_client/mock_image_edit_client.py`

如果 `ComfyUIClient` 已支持 img2img，也可以挂入该 provider_type 的执行器列表。

---

## 8. 图片切割服务

建议新增：

- `backend/core/services/multi_grid_image_service.py`

只负责多宫格节点相关的图片处理，不负责高清还原。

建议方法：

- `load_source_image(...)`
- `validate_grid_config(...)`
- `split_image(...)`
- `save_tiles(...)`
- `build_multi_grid_output(...)`

切割建议使用 `Pillow`。

注意：

- 这个服务只负责生成后的切割。
- 不要在这里调用 `image_edit` 模型。

---

## 9. 提示词管理改造

## 9.1 多宫格图片模板

`multi_grid_image` 模板仍然属于文生图模板。

建议可用变量：

- `scene_description`
- `narration_text`
- `image_prompt`
- `grid_rows`
- `grid_cols`
- `style`
- `character`

模板目标：

- 指导模型一次性生成带多个分格构图的图片。

## 9.2 图片编辑模板

`image_edit` 模板属于图片编辑阶段模板。

建议可用变量：

- `source_image_url`
- `tile_index`
- `scene_description`
- `narration_text`
- `image_prompt`

模板目标：

- 指导模型对单张已有图做高清修复或细节增强。

## 9.3 调试工作台

调试映射需改为：

- `multi_grid_image -> text2image`
- `image_edit -> image_edit`

并分别支持：

- 多宫格大图生成预览；
- 单张图片编辑结果预览。

---

## 10. 画布设计

## 10.1 推荐节点顺序

建议画布链路变成：

- 文案改写
- 分镜
- 文生图
- 多宫格图片
- 图片编辑
- 运镜
- 图生视频

说明：

- `multi_grid_image` 和 `image_generation` 可以并列视为两种出图路径；
- `image_edit` 是后处理节点，可接在二者之后。

## 10.2 多宫格图片节点功能

建议新增：

- `frontend/src/components/canvas/MultiGridImageNode.vue`

节点功能：

- 配置多宫格模板参数；
- 选择文生图模型；
- 执行生成；
- 查看大图；
- 查看切片结果；
- 选择部分 tile 发送到图片编辑节点。

## 10.3 图片编辑节点功能

建议新增：

- `frontend/src/components/canvas/ImageEditNode.vue`

节点功能：

- 选择输入来源；
- 显示待编辑图片列表；
- 选择图片编辑模型；
- 输入图片编辑提示词；
- 执行逐图高清；
- 查看编辑结果；
- 选择最终图。

---

## 11. 项目序列化改造

当前项目详情会把多个阶段的数据整合进 storyboard 结果中。新增两个阶段后，建议在 storyboard 维度新增：

```json
{
  "multi_grid_image": {
    "template_enabled": true,
    "tasks": [...],
    "tiles": [...]
  },
  "image_edit": {
    "template_enabled": true,
    "tasks": [...],
    "results": [...]
  }
}
```

需同步修改：

- `backend/apps/projects/serializers.py`
- `backend/apps/projects/views.py`
- `frontend/src/store/modules/projects.js`
- 画布节点读取逻辑

---

## 12. 实施顺序建议

### Phase 1：新增图片编辑模型类型

目标：先让模型管理支持 `image_edit`。

包括：

- `provider_type=image_edit`
- 执行器列表
- 后端校验
- 前端模型管理

### Phase 2：新增两个阶段枚举

目标：让提示词管理、项目阶段、调试工作台都认识：

- `multi_grid_image`
- `image_edit`

### Phase 3：先做多宫格节点

目标：打通“生成多宫格 + 切片输出”。

包括：

- `multi_grid_image_stage`
- `MultiGridImageTask`
- `MultiGridTile`
- 画布节点

### Phase 4：再做图片编辑节点

目标：打通“读取切片 + 逐张高清”。

包括：

- `image_edit_stage`
- `EditedImageTask`
- `EditedImageResult`
- 画布节点

---

## 13. 第一版边界建议

第一版建议收敛到以下范围：

- 多宫格节点只支持手动指定行列数；
- 先不做自动识别网格；
- 图片编辑节点只支持整图高清，不做 mask 局部编辑；
- 多宫格节点生成后立即切片；
- 图片编辑节点支持按 tile 勾选执行。

---

## 14. 最终结论

按当前澄清，正确方案应是：

1. **多宫格图片节点**：本质是 `text2image` 阶段变体，负责“生成一张多宫格图并切割成多张图”。
2. **图片编辑节点**：是独立 `image_edit` 阶段，负责“接收已有图片并逐张执行高清还原/图生图”。
3. **模型管理**：只需要为图片编辑节点新增 `image_edit` 类型模型；多宫格节点继续使用 `text2image` 模型。
4. **提示词管理**：新增两个阶段模板 `multi_grid_image` 和 `image_edit`。
5. **画布编排**：多宫格节点产出切片，图片编辑节点消费切片并输出高清图。

这是与你当前需求最一致、职责最清晰、也最便于后续扩展的实现方式。
