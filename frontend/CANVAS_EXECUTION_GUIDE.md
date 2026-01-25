# ProjectCanvas 节点执行功能说明

## 概述

已为 ProjectCanvas 中的各个节点（文生图、运镜、图生视频）接入了执行操作,参考了 StageContent 组件的 `handleExecute` 方法实现。

## 实现的功能

### 1. 文生图节点 (ImageGenNode)

**功能:**
- 点击"生成"按钮执行文生图
- 支持自定义提示词
- 显示生成状态（pending/processing/completed/failed）
- 支持重新生成

**执行流程:**
```
用户点击生成按钮
→ ImageGenNode.handleGenerate()
→ emit('generate', { storyboardId, prompt })
→ ProjectCanvas.handleGenerateImage()
→ emit('execute-stage', { stageType: 'image_generation', inputData })
→ ProjectDetail.handleGenerateImage()
→ ProjectDetail.handleExecuteStage()
→ Vuex executeStage action
→ 调用后端 API
```

**输入数据格式:**
```javascript
{
  storyboard_ids: [storyboardId],
  scenes: [{
    scene_number: 1,
    narration: "旁白文本",
    visual_prompt: "视觉提示词",
    shot_type: "标准镜头"
  }]
}
```

### 2. 运镜节点 (CameraNode)

**功能:**
- 点击"生成"按钮执行运镜生成
- 支持选择运镜类型（静态、推进、拉远等）
- 自动检查前置条件（需要先生成图片）
- 显示运镜参数（速度、强度）

**执行流程:**
```
用户点击生成按钮
→ CameraNode.handleGenerate()
→ emit('generate', { storyboardId, movementType })
→ ProjectCanvas.handleGenerateCamera()
→ 检查是否有图片
→ emit('execute-stage', { stageType: 'camera_movement', inputData })
→ ProjectDetail.handleGenerateCamera()
→ ProjectDetail.handleExecuteStage()
→ Vuex executeStage action
→ 调用后端 API
```

**输入数据格式:**
```javascript
{
  storyboard_ids: [storyboardId],
  scenes: [{
    scene_number: 1,
    image_url: "https://...",
    movement_type: "zoom_in" // 或 "auto"
  }]
}
```

### 3. 图生视频节点 (VideoGenNode)

**功能:**
- 点击"生成"按钮执行图生视频
- 自动检查前置条件（需要先生成图片和运镜）
- 显示视频预览
- 显示视频信息（时长、分辨率、帧率）

**执行流程:**
```
用户点击生成按钮
→ VideoGenNode.handleGenerate()
→ emit('generate', { storyboardId })
→ ProjectCanvas.handleGenerateVideo()
→ 检查是否有图片和运镜
→ emit('execute-stage', { stageType: 'video_generation', inputData })
→ ProjectDetail.handleGenerateVideo()
→ ProjectDetail.handleExecuteStage()
→ Vuex executeStage action
→ 调用后端 API
```

**输入数据格式:**
```javascript
{
  storyboard_ids: [storyboardId],
  scenes: [{
    scene_number: 1,
    image_url: "https://...",
    camera_movement: {
      movement_type: "zoom_in",
      movement_params: {
        speed: "medium",
        intensity: "high"
      }
    }
  }]
}
```

## 状态管理

### 节点状态

每个节点支持以下状态:
- `pending`: 待执行
- `processing`: 执行中
- `completed`: 已完成
- `failed`: 失败

### 执行状态跟踪

ProjectCanvas 维护了一个 `executingNodes` 对象来跟踪正在执行的节点:

```javascript
executingNodes: {
  images: { storyboardId: true/false },
  cameras: { storyboardId: true/false },
  videos: { storyboardId: true/false }
}
```

**状态更新时机:**
1. 点击生成按钮时,设置为 `true`
2. WebSocket 接收到更新时,检查数据是否已生成,自动清除状态
3. 发生错误时,立即清除状态

## 实时更新

### WebSocket 集成

ProjectDetail 已配置 WebSocket 连接:

```javascript
connectWebSocket() {
  websocketClient.connect(projectId);

  // 监听阶段更新
  websocketClient.on('stage_update', (data) => {
    this.fetchData(true); // 刷新数据,保持滚动位置
  });

  // 监听项目更新
  websocketClient.on('project_update', (data) => {
    this.project = data.project;
  });
}
```

当后端完成生成任务时,会通过 WebSocket 推送更新,前端自动刷新数据并更新节点状态。

## 错误处理

### 前置条件检查

- **文生图**: 需要有提示词
- **运镜**: 需要先完成文生图
- **图生视频**: 需要先完成文生图和运镜

### 错误提示

所有节点都会在以下情况显示错误提示:
- 缺少必要数据
- API 调用失败
- 后端返回错误

### 用户反馈

使用 `this.$message` 显示操作反馈:
- `info`: 开始执行
- `success`: 执行成功
- `warning`: 前置条件不满足
- `error`: 执行失败

## 使用示例

### 1. 生成图片

```javascript
// 在 ImageGenNode 中
<button @click="handleGenerate">生成图片</button>

// 方法
handleGenerate() {
  if (!this.localPrompt.trim()) {
    this.$message?.warning('请先输入提示词');
    return;
  }
  this.$emit('generate', {
    storyboardId: this.storyboardId,
    prompt: this.localPrompt
  });
}
```

### 2. 生成运镜

```javascript
// 在 CameraNode 中
<select v-model="localMovementType">
  <option value="zoom_in">推进</option>
  <option value="pan_left">左移</option>
</select>
<button @click="handleGenerate">生成运镜</button>

// 方法
handleGenerate() {
  if (!this.canGenerate) {
    this.$message?.warning('请先完成图片生成');
    return;
  }
  this.$emit('generate', {
    storyboardId: this.storyboardId,
    movementType: this.localMovementType
  });
}
```

### 3. 生成视频

```javascript
// 在 VideoGenNode 中
<button @click="handleGenerate">生成视频</button>

// 方法
handleGenerate() {
  if (!this.canGenerate) {
    this.$message?.warning('请先完成运镜生成');
    return;
  }
  this.$emit('generate', {
    storyboardId: this.storyboardId
  });
}
```

## 调试

### 控制台日志

所有关键步骤都有日志输出:

```javascript
console.log('[ImageGenNode] 生成失败:', error);
console.log('[ProjectCanvas] 生成图片:', { storyboardId, prompt });
console.log('[ProjectDetail] 生成图片:', { stageType, inputData, storyboardId });
```

### 查看执行状态

在 Vue DevTools 中可以查看:
- `ProjectCanvas.executingNodes`: 当前执行状态
- `ProjectDetail.stages`: 所有阶段数据
- `ProjectDetail.storyboards`: 分镜数据

## 后续优化建议

1. **进度显示**: 添加进度条显示生成进度
2. **批量操作**: 支持批量生成多个分镜
3. **取消操作**: 支持取消正在执行的任务
4. **重试机制**: 失败后自动重试
5. **缓存优化**: 缓存已生成的结果,避免重复生成
6. **预览功能**: 在生成前预览效果
7. **历史记录**: 保存生成历史,支持回滚

## 相关文件

- `frontend/src/components/canvas/ImageGenNode.vue` - 文生图节点
- `frontend/src/components/canvas/CameraNode.vue` - 运镜节点
- `frontend/src/components/canvas/VideoGenNode.vue` - 图生视频节点
- `frontend/src/components/canvas/ProjectCanvas.vue` - 画布容器
- `frontend/src/views/projects/ProjectDetail.vue` - 项目详情页
- `frontend/src/components/projects/StageContent.vue` - 阶段内容组件（参考实现）
- `frontend/src/api/projects.js` - API 服务
- `frontend/src/services/websocketClient.js` - WebSocket 客户端
