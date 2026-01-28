# 文案改写SSE流式展示功能说明

## 功能概述

文案改写节点现在支持通过SSE (Server-Sent Events) 实时接收和展示AI生成的内容，用户可以在textarea中看到文字逐步生成的过程。

## 实现原理

### 1. 前端流程

```
用户点击"执行改写"
  ↓
发送POST请求到 /api/v1/projects/projects/{projectId}/execute_stage/
  (携带 use_streaming: true 参数)
  ↓
使用Fetch API读取响应流
  ↓
解析SSE格式的数据 (data: {...})
  ↓
实时更新textarea内容
  ↓
完成后关闭流
```

### 2. SSE消息类型

后端通过SSE推送以下类型的消息：

- **`token`**: 流式文本片段
  ```json
  {
    "type": "token",
    "content": "这是",
    "full_text": "这是一段生成的文本..."
  }
  ```

- **`done`**: 生成完成
  ```json
  {
    "type": "done",
    "full_text": "完整的改写后文案...",
    "stage": {
      "id": "xxx",
      "status": "completed"
    }
  }
  ```

- **`error`**: 生成失败
  ```json
  {
    "type": "error",
    "error": "错误信息",
    "stage": {
      "id": "xxx",
      "status": "failed",
      "error_message": "详细错误"
    }
  }
  ```

### 3. 关键代码修改

#### RewriteNodeExpanded.vue

**新增数据属性：**
```javascript
data() {
  return {
    eventSource: null,     // EventSource实例（预留）
    streamingText: ''      // 流式接收的文本
  };
}
```

**新增方法：**
- `handleSSEMessage(data)`: 处理SSE消息，根据type分发处理

**修改方法：**
- `handleExecute()`: 使用Fetch API发送POST请求，启用SSE流式响应
  - 设置 `use_streaming: true` 参数
  - 使用 `response.body.getReader()` 读取流
  - 解析 `data: {...}` 格式的SSE消息
  - 调用 `handleSSEMessage()` 处理每条消息

## 使用说明

### 前端使用

1. 用户在项目详情页面点击"文案改写"节点
2. 点击"执行改写"按钮
3. 系统发送POST请求，启用SSE流式响应
4. 在textarea中实时看到文字逐步生成
5. 生成完成后自动关闭流

### 后端要求

后端需要在 `execute_stage` 接口中：

1. 接收 `use_streaming: true` 参数
2. 返回 `text/event-stream` 响应
3. 推送SSE格式的消息：

```python
# 在视图中
def _execute_stage_streaming(self, project, stage_name, input_data):
    # 使用队列在异步和同步之间传递数据
    data_queue = queue.Queue()

    # 异步生成器
    async def async_producer():
        processor = LLMStageProcessor(stage_type=stage_name)
        async for chunk in processor.process_stream(
            project_id=str(project.id),
            input_data=input_data
        ):
            event_data = json.dumps(chunk, ensure_ascii=False)
            data_queue.put(f"data: {event_data}\n\n".encode("utf-8"))

    # 同步生成器
    def sync_event_stream():
        while True:
            chunk = data_queue.get(timeout=300)
            if chunk is None:
                break
            yield chunk

    # 返回SSE响应
    response = StreamingHttpResponse(
        sync_event_stream(),
        content_type="text/event-stream; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache, no-transform"
    response["X-Accel-Buffering"] = "no"
    return response
```

## 技术细节

### SSE vs WebSocket

选择SSE的原因：
- **单向通信**：文案改写只需要服务器推送数据到客户端
- **自动重连**：浏览器原生支持断线重连
- **HTTP协议**：无需额外的WebSocket服务器配置
- **简单易用**：基于标准HTTP，易于调试和部署

### Fetch API流式读取

使用 `response.body.getReader()` 读取流：

```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value, { stream: true });
  // 处理chunk
}
```

### 数据更新机制

使用Vue的 `$set` 方法确保响应式更新：

```javascript
this.$set(this.data, 'rewritten_text', this.streamingText);
```

### 错误处理

- HTTP错误：捕获fetch异常，显示错误提示
- SSE解析错误：捕获JSON.parse异常，记录日志
- 任务失败：接收error类型消息，显示失败原因

## 测试步骤

1. 启动后端服务（**必须使用ASGI模式**）：
   ```bash
   cd backend
   ./run_asgi.sh
   # 或
   daphne -b 0.0.0.0 -p 8000 config.asgi:application
   ```

2. 启动前端：
   ```bash
   cd frontend
   npm run dev
   ```

3. 访问项目详情页面，点击"执行改写"

4. 观察：
   - 浏览器Network标签中看到 `text/event-stream` 响应
   - textarea中文字逐步生成
   - 控制台输出SSE消息日志

## 注意事项

1. **必须使用ASGI服务器**：SSE需要真正的流式响应，Django的runserver（WSGI）会缓冲完整响应
2. **CORS配置**：确保后端允许跨域请求（开发环境）
3. **认证Token**：请求需要携带Authorization头
4. **超时处理**：后端设置了5分钟超时，前端需要处理超时情况
5. **网络延迟**：流式展示的流畅度取决于网络延迟和AI生成速度

## 调试技巧

### 查看SSE消息

在浏览器控制台：
```javascript
// 查看所有SSE消息
console.log('[RewriteNode] 收到SSE消息:', data);
```

在浏览器Network标签：
- 找到 `execute_stage` 请求
- 查看Response标签，可以看到实时的SSE消息流

### 模拟SSE响应

可以使用curl测试后端SSE接口：
```bash
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage_name":"rewrite","input_data":{"original_topic":"测试"},"use_streaming":true}' \
  http://localhost:8000/api/v1/projects/projects/PROJECT_ID/execute_stage/
```

## 未来优化

- [ ] 添加打字机效果动画
- [ ] 显示生成进度条（基于token数量）
- [ ] 支持暂停/继续生成
- [ ] 添加生成速度控制
- [ ] 支持多轮对话式改写
- [ ] 添加重连机制（当前使用Fetch，需要手动实现）
- [ ] 优化大文本渲染性能（虚拟滚动）
