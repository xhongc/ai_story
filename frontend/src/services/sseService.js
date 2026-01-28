/**
 * SSE服务 - 统一的Server-Sent Events客户端
 * 对接后端 ProjectStageSSEView 接口
 *
 * 后端接口:
 * - 单阶段: GET /api/v1/sse/projects/{project_id}/stages/{stage_name}/
 * - 所有阶段: GET /api/v1/sse/projects/{project_id}/
 */

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8010';

/**
 * SSE客户端类
 */
export class SSEClient {
  constructor() {
    this.eventSource = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
    this.reconnectDelay = 1000; // 1秒
  }

  /**
   * 连接到SSE端点
   * @param {string} url - SSE端点URL
   * @param {Object} options - 配置选项
   * @param {boolean} options.autoReconnect - 是否自动重连
   * @returns {SSEClient} 返回自身以支持链式调用
   */
  connect(url, options = {}) {
    const { autoReconnect = false } = options;

    // 如果已有连接，先关闭
    if (this.eventSource) {
      this.disconnect();
    }

    console.log('[SSE] 正在连接:', url);

    try {
      // 创建EventSource连接
      this.eventSource = new EventSource(url);

      // 监听连接打开
      this.eventSource.onopen = () => {
        console.log('[SSE] 连接已建立');
        this.reconnectAttempts = 0; // 重置重连计数
        this.emit('open', { url });
      };

      // 监听消息
      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // console.log('[SSE] 收到消息:', data);

          // 触发通用message事件
          this.emit('message', data);

          // 根据type触发特定事件
          if (data.type) {
            this.emit(data.type, data);
          }

          // 如果收到done或error，自动关闭连接
          if (data.type === 'done' || data.type === 'error' || data.type === 'stream_end') {
            console.log('[SSE] 收到结束信号，准备关闭连接');
            setTimeout(() => this.disconnect(), 100);
          }
        } catch (error) {
          console.error('[SSE] 消息解析失败:', error, '原始数据:', event.data);
          this.emit('parse_error', { error, rawData: event.data });
        }
      };

      // 监听错误
      this.eventSource.onerror = (error) => {
        console.error('[SSE] 连接错误:', error);
        this.emit('error', { error, readyState: this.eventSource?.readyState });

        // 如果连接关闭且启用自动重连
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.emit('close', { url });

          if (autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[SSE] 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => {
              this.connect(url, options);
            }, this.reconnectDelay * this.reconnectAttempts);
          } else {
            this.cleanup();
          }
        }
      };
    } catch (error) {
      console.error('[SSE] 创建连接失败:', error);
      this.emit('error', { error });
    }

    return this;
  }

  /**
   * 监听事件
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数
   * @returns {SSEClient} 返回自身以支持链式调用
   */
  on(event, handler) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(handler);
    return this;
  }

  /**
   * 移除事件监听
   * @param {string} event - 事件名称
   * @param {Function} handler - 事件处理函数（可选，不传则移除所有）
   * @returns {SSEClient} 返回自身以支持链式调用
   */
  off(event, handler) {
    if (!this.listeners[event]) return this;

    if (handler) {
      this.listeners[event] = this.listeners[event].filter((h) => h !== handler);
    } else {
      delete this.listeners[event];
    }
    return this;
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {*} data - 事件数据
   */
  emit(event, data) {
    if (!this.listeners[event]) return;

    this.listeners[event].forEach((handler) => {
      try {
        handler(data);
      } catch (error) {
        console.error(`[SSE] 事件处理器执行失败 (${event}):`, error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.eventSource) {
      console.log('[SSE] 正在关闭连接');
      this.eventSource.close();
      this.cleanup();
    }
  }

  /**
   * 清理资源
   */
  cleanup() {
    this.eventSource = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
  }

  /**
   * 获取连接状态
   * @returns {number} EventSource状态码
   */
  getReadyState() {
    if (!this.eventSource) return EventSource.CLOSED;
    return this.eventSource.readyState;
  }

  /**
   * 是否已连接
   * @returns {boolean}
   */
  isConnected() {
    return this.eventSource && this.eventSource.readyState === EventSource.OPEN;
  }
}

/**
 * 创建项目阶段SSE客户端
 * @param {string} projectId - 项目ID
 * @param {string} stageName - 阶段名称 (rewrite/storyboard/image_generation/camera_movement/video_generation)
 * @param {Object} options - 配置选项
 * @param {boolean} options.autoReconnect - 是否自动重连
 * @returns {SSEClient} SSE客户端实例
 */
export function createProjectStageSSE(projectId, stageName, options = {}) {
  const client = new SSEClient();
  const url = `${API_BASE_URL}/api/v1/projects/sse/projects/${projectId}/stages/${stageName}/`;
  client.connect(url, options);
  return client;
}

/**
 * 创建项目所有阶段SSE客户端
 * @param {string} projectId - 项目ID
 * @param {Object} options - 配置选项
 * @param {boolean} options.autoReconnect - 是否自动重连
 * @returns {SSEClient} SSE客户端实例
 */
export function createProjectAllStagesSSE(projectId, options = {}) {
  const client = new SSEClient();
  const url = `${API_BASE_URL}/api/v1/projects/sse/projects/${projectId}/`;
  client.connect(url, options);
  return client;
}

/**
 * SSE事件类型常量
 */
export const SSE_EVENT_TYPES = {
  // 连接事件
  OPEN: 'open',
  CLOSE: 'close',
  ERROR: 'error',
  PARSE_ERROR: 'parse_error',
  MESSAGE: 'message',

  // 业务事件
  CONNECTED: 'connected',
  TOKEN: 'token',
  STAGE_UPDATE: 'stage_update',
  PROGRESS: 'progress',
  DONE: 'done',
  STREAM_END: 'stream_end',
};

/**
 * Vue 2 Mixin - 用于在组件中使用SSE
 *
 * 使用方法:
 * import { sseClientMixin } from '@/services/sseService';
 *
 * export default {
 *   mixins: [sseClientMixin],
 *   mounted() {
 *     this.connectSSE(this.projectId, this.stageName);
 *   }
 * }
 */
export const sseClientMixin = {
  data() {
    return {
      sseClient: null,
      sseConnected: false,
      sseMessages: [],
      sseError: null,
    };
  },
  methods: {
    /**
     * 连接SSE
     * @param {string} projectId - 项目ID
     * @param {string} stageName - 阶段名称（可选）
     * @param {Object} options - 配置选项
     */
    connectSSE(projectId, stageName = null, options = {}) {
      // 断开已有连接
      this.disconnectSSE();

      // 创建新连接
      if (stageName) {
        this.sseClient = createProjectStageSSE(projectId, stageName, options);
      } else {
        this.sseClient = createProjectAllStagesSSE(projectId, options);
      }

      // 监听事件
      this.sseClient
        .on('open', () => {
          this.sseConnected = true;
          this.sseError = null;
          this.onSSEOpen && this.onSSEOpen();
        })
        .on('message', (data) => {
          this.sseMessages.push(data);
          this.onSSEMessage && this.onSSEMessage(data);
        })
        .on('connected', (data) => {
          this.onSSEConnected && this.onSSEConnected(data);
        })
        .on('token', (data) => {
          this.onSSEToken && this.onSSEToken(data);
        })
        .on('stage_update', (data) => {
          this.onSSEStageUpdate && this.onSSEStageUpdate(data);
        })
        .on('progress', (data) => {
          this.onSSEProgress && this.onSSEProgress(data);
        })
        .on('done', (data) => {
          this.onSSEDone && this.onSSEDone(data);
        })
        .on('error', (data) => {
          this.sseError = data.error;
          this.onSSEError && this.onSSEError(data);
        })
        .on('close', () => {
          this.sseConnected = false;
          this.onSSEClose && this.onSSEClose();
        });
    },

    /**
     * 断开SSE连接
     */
    disconnectSSE() {
      if (this.sseClient) {
        this.sseClient.disconnect();
        this.sseClient = null;
        this.sseConnected = false;
      }
    },

    /**
     * 清空SSE消息
     */
    clearSSEMessages() {
      this.sseMessages = [];
    },
  },
  beforeDestroy() {
    // 组件销毁时自动断开连接
    this.disconnectSSE();
  },
};

export default {
  SSEClient,
  createProjectStageSSE,
  createProjectAllStagesSSE,
  SSE_EVENT_TYPES,
  sseClientMixin,
};
