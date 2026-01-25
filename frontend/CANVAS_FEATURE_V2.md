# 项目详情页画布功能 v2.0

## 功能概述

项目详情页的"工作流画布"现在支持完全在画布上进行所有操作，无需切换Tab。所有节点都是可交互的，包含输入框、按钮和详细信息展示。

## 核心特性

### 1. 文案改写节点 (RewriteNodeExpanded)
**尺寸**: 480px × 600px

**功能**:
- ✅ 显示原始文案（只读）
- ✅ 改写后文案编辑框（可编辑）
- ✅ 状态指示器（待执行/执行中/已完成/失败）
- ✅ 操作按钮：
  - 执行改写（pending/failed状态）
  - 保存修改（completed状态）
  - 重试（failed状态）
  - 重新生成（completed状态）
- ✅ 元数据显示（使用模型、生成时间）

**交互**:
- 直接在节点上编辑文案
- 点击按钮执行操作
- 实时显示执行状态

### 2. 分镜卡片节点 (StoryboardCardExpanded)
**尺寸**: 380px × 650px
**布局**: 网格布局，每行2个卡片

**功能**:
- ✅ 分镜编号和状态徽章
- ✅ 时长显示
- ✅ 可编辑字段：
  - 场景描述（textarea）
  - 旁白文案（textarea）
  - 文生图提示词（textarea）
- ✅ 子流程状态展示：
  - 文生图：状态 + 图片预览 + 生成按钮
  - 运镜：状态 + 运镜类型 + 生成按钮
  - 图生视频：状态 + 视频预览 + 生成按钮
- ✅ 操作按钮：
  - 保存修改
  - 删除分镜

**交互**:
- 直接编辑分镜信息
- 点击生成按钮执行对应阶段
- 预览生成的图片和视频
- 按钮根据前置条件自动启用/禁用

### 3. 画布容器 (FlowCanvas)
**功能**:
- ✅ 缩放控制（放大/缩小/重置）
- ✅ 鼠标拖动浏览
- ✅ 滚轮缩放
- ✅ SVG连接线（贝塞尔曲线）
- ✅ 连接线颜色根据状态变化

## 布局设计

```
画布布局（横向流程）:

[文案改写节点]  →  [分镜1] [分镜2]
(100, 100)         [分镜3] [分镜4]
480×600            [分镜5] [分镜6]
                   ...
                   (700, 100起始)
                   380×650每个
                   每行2个，间距30px
```

## 数据流

```
ProjectDetail.vue
  ├── 获取项目数据
  ├── 获取阶段数据
  ├── 提取分镜数据
  └── ProjectCanvas.vue
      ├── RewriteNodeExpanded
      │   ├── 显示原始文案
      │   ├── 编辑改写文案
      │   └── 执行/保存操作
      └── StoryboardCardExpanded × N
          ├── 编辑分镜信息
          ├── 生成图片
          ├── 生成运镜
          ├── 生成视频
          └── 保存/删除操作
```

## 事件处理

### ProjectCanvas 发出的事件:
- `execute-stage`: 执行阶段（文案改写）
- `save-stage`: 保存阶段数据
- `generate-image`: 生成图片
- `generate-camera`: 生成运镜
- `generate-video`: 生成视频
- `save-storyboard`: 保存分镜
- `delete-storyboard`: 删除分镜

### ProjectDetail 处理方法:
```javascript
handleExecuteStage({ stageType, inputData })
handleSaveStage({ stageType, outputData })
handleGenerateImage({ storyboardId, prompt })
handleGenerateCamera({ storyboardId })
handleGenerateVideo({ storyboardId })
handleSaveStoryboard({ storyboardId, data })
handleDeleteStoryboard(storyboardId)
```

## 状态管理

### 节点状态:
- `pending`: 待执行（灰色边框）
- `processing`: 执行中（蓝色边框 + 动画）
- `completed`: 已完成（绿色边框）
- `failed`: 失败（红色边框）

### 按钮状态:
- 根据节点状态显示不同按钮
- 根据前置条件启用/禁用按钮
- 执行中显示loading状态

## 样式特点

### 文案改写节点:
```css
- 宽度: 480px
- 背景: 根据状态变化
- 边框: 2px，颜色根据状态
- 圆角: 1rem
- 阴影: 悬停时加深
- 内部分区: 头部/原始文案/改写文案/操作按钮/元数据
```

### 分镜卡片:
```css
- 宽度: 380px
- 子流程: 横向排列，箭头连接
- 预览区: 16:9比例
- 按钮: 小尺寸，全宽
- 状态颜色: 背景和边框同步变化
```

## 使用流程

### 1. 文案改写流程:
1. 查看原始文案
2. 点击"执行改写"按钮
3. 等待AI生成（节点显示processing状态）
4. 查看生成结果，可手动编辑
5. 点击"保存修改"保存
6. 或点击"重新生成"重新执行

### 2. 分镜生成流程:
1. 文案改写完成后，分镜自动生成
2. 编辑分镜信息（场景描述、旁白、提示词）
3. 点击"保存修改"保存编辑

### 3. 图片生成流程:
1. 确认文生图提示词
2. 点击"生成图片"按钮
3. 等待生成完成
4. 查看图片预览

### 4. 运镜生成流程:
1. 图片生成完成后，按钮自动启用
2. 点击"生成运镜"按钮
3. 查看运镜类型

### 5. 视频生成流程:
1. 运镜生成完成后，按钮自动启用
2. 点击"生成视频"按钮
3. 等待生成完成
4. 播放视频预览

## 技术实现

### 组件文件:
```
frontend/src/components/canvas/
├── FlowCanvas.vue                 # 画布容器（已有）
├── RewriteNodeExpanded.vue        # 文案改写节点（新）
├── StoryboardCardExpanded.vue     # 分镜卡片（新）
└── ProjectCanvas.vue              # 主画布（更新）
```

### 关键技术:
1. **纯CSS实现**: 无第三方依赖
2. **响应式布局**: 自动计算节点位置
3. **事件冒泡**: 从子组件向上传递事件
4. **状态同步**: 通过props和events保持数据一致
5. **条件渲染**: 根据状态显示不同UI

## 待实现的API

以下API需要后端支持：

1. **文生图API**: `POST /api/v1/storyboards/{id}/generate-image/`
2. **运镜生成API**: `POST /api/v1/storyboards/{id}/generate-camera/`
3. **图生视频API**: `POST /api/v1/storyboards/{id}/generate-video/`
4. **保存分镜API**: `PATCH /api/v1/storyboards/{id}/`
5. **删除分镜API**: `DELETE /api/v1/storyboards/{id}/`

## 后续优化

### 功能增强:
- [ ] 添加批量操作（批量生成图片/视频）
- [ ] 支持拖拽调整分镜顺序
- [ ] 添加分镜复制功能
- [ ] 支持导出单个分镜
- [ ] 添加撤销/重做功能

### 性能优化:
- [ ] 大量分镜时使用虚拟滚动
- [ ] 图片/视频懒加载
- [ ] 节点位置缓存

### 用户体验:
- [ ] 添加快捷键支持
- [ ] 添加操作提示/引导
- [ ] 优化移动端体验
- [ ] 添加全屏模式

## 注意事项

1. **数据同步**: 所有操作都会触发数据刷新
2. **状态管理**: 节点状态由后端返回的stage数据决定
3. **错误处理**: 所有操作都有try-catch和用户提示
4. **按钮禁用**: 根据前置条件自动禁用按钮，防止误操作
5. **WebSocket**: 支持实时状态更新（已集成）
