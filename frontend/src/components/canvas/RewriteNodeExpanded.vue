<template>
  <div
    class="rewrite-node-expanded"
    :class="`status-${effectiveStatus}`"
    :style="nodeStyle"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        <h3 class="node-title">文案改写</h3>
      </div>
      <div class="header-right">
        <!-- 操作图标按钮 -->
        <div class="action-icons">
          <!-- 运行改写图标 -->
          <button
            class="icon-btn"
            :class="{ 'icon-btn-disabled': status === 'processing' || isExecuting || isGeneratingStoryboard }"
            :disabled="status === 'processing' || isExecuting || isGeneratingStoryboard"
            @click.stop="handleQuickExecute('rewrite')"
            title="运行改写"
          >
            <span v-if="isExecuting && !isGeneratingStoryboard" class="loading loading-spinner loading-xs"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          <!-- 生成分镜图标 -->
          <button
            class="icon-btn"
            :class="{ 'icon-btn-disabled': status === 'processing' || isGeneratingStoryboard || isExecuting }"
            :disabled="status === 'processing' || isGeneratingStoryboard || isExecuting"
            @click.stop="handleGenerateStoryboard('storyboard')"
            title="生成分镜"
          >
            <span v-if="isGeneratingStoryboard" class="loading loading-spinner loading-xs"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 原始文案 -->
    <div class="node-section">
      <label class="section-label">原始文案</label>
      <div
        class="original-text"
        @wheel.stop
        @mousedown.stop
      >{{ data.original_text || '暂无原始文案' }}</div>
    </div>

    <!-- 改写后文案 -->
    <div class="node-section">
      <label class="section-label">改写后文案</label>
      <textarea
        v-model="data.rewritten_text"
        class="textarea textarea-bordered w-full"
        rows="8"
        placeholder="改写后的文案将显示在这里..."
        :disabled="status === 'processing'"
        @wheel.stop
        @mousedown.stop
      ></textarea>
    </div>

    <!-- 元数据信息 -->
    <div v-if="data && data.model_provider" class="node-metadata">
      <div class="metadata-item">
        <span class="metadata-label">使用模型:</span>
        <span class="metadata-value">{{ data.model_provider.model_name || 'N/A' }}</span>
      </div>
      <div class="metadata-item">
        <span class="metadata-label">生成时间:</span>
        <span class="metadata-value">{{ formatDate(data.updated_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { createProjectStageSSE } from '@/services/sseService';
import projectsAPI from '@/api/projects';

export default {
  name: 'RewriteNodeExpanded',
  props: {
    status: {
      type: String,
      default: 'pending'
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    data: {
      type: Object,
      default: null
    },
    originalTopic: {
      type: String,
      default: ''
    },
    projectId: {
      type: [String, Number],
      required: true
    }
  },
  data() {
    return {
      rewrittenContent: '',
      isExecuting: false,
      isSaving: false,
      isGeneratingStoryboard: false,
      sseClient: null,
      streamingText: '' // 用于存储流式接收的文本
    };
  },
  computed: {
    nodeStyle() {
      return {
        position: 'absolute',
        left: `${this.position.x}px`,
        top: `${this.position.y}px`,
      };
    },
    // 计算有效状态：如果正在执行改写或生成分镜，显示processing状态
    effectiveStatus() {
      if (this.isExecuting || this.isGeneratingStoryboard) {
        return 'processing';
      }
      return this.status;
    },
    statusText() {
      const statusMap = {
        pending: '待执行',
        processing: '执行中',
        completed: '已完成',
        failed: '失败'
      };
      return statusMap[this.status] || '未知';
    }
  },
  watch: {
    data: {
      immediate: true,
      handler(newData) {
        if (newData && newData.rewritten_content) {
          this.rewrittenContent = newData.rewritten_content;
        }
      }
    }
  },
  methods: {
    async handleQuickExecute(mode='rewrite') {
      if (this.status === 'processing' || this.isExecuting) {
        return;
      }
      await this.handleExecute(mode);
    },

    async handleGenerateStoryboard(mode='storyboard') {
      if (this.status === 'processing' || this.isGeneratingStoryboard) {
        return;
      }
      await this.handleExecute(mode);
    },

    async handleExecute(mode) {
      console.log('handleExecute', mode);
      this.isExecuting = true;
      if (mode === 'storyboard') {
        this.isGeneratingStoryboard = true;
      }
      this.streamingText = ''; // 清空之前的流式文本

      try {
        // 使用API方法发送POST请求启动任务
        await projectsAPI.executeStage(
          this.projectId,
          mode,
          { original_topic: this.originalTopic },
          true // 启用SSE流式输出
        );

        // 断开已有的SSE连接
        if (this.sseClient) {
          this.sseClient.disconnect();
          this.sseClient = null;
        }

        // 使用sseService创建SSE客户端连接
        this.sseClient = createProjectStageSSE(this.projectId, mode, {
          autoReconnect: false
        });

        // 监听SSE事件
        this.sseClient
          .on('open', () => {
            console.log('[RewriteNode] SSE连接已建立');
          })
          .on('token', (data) => {
            // 流式token，追加到文本
            if (data.content) {
              this.streamingText += data.content;
              // 实时更新到data中，触发textarea更新
              if (this.data) {
                this.$set(this.data, 'rewritten_text', this.streamingText);
              }
            }
          })
          .on('done', (data) => {
            // 生成完成
            console.log('[RewriteNode] 生成完成, mode:', mode);
            this.isExecuting = false;
            this.isGeneratingStoryboard = false;

            // 使用完整文本（如果有）
            if (data.full_text) {
              this.streamingText = data.full_text;
              if (this.data) {
                this.$set(this.data, 'rewritten_text', this.streamingText);
              }
            }

            // 根据模式显示不同的成功消息
            if (mode === 'storyboard') {
              this.$message?.success('分镜生成完成');
              // 触发刷新事件，通知父组件更新画布
              this.$emit('storyboard-generated');
            } else {
              this.$message?.success('文案改写完成');
            }

            // 关闭SSE连接
            if (this.sseClient) {
              this.sseClient.disconnect();
              this.sseClient = null;
            }
          })
          .on('error', (data) => {
            // 生成失败
            console.error('[RewriteNode] 生成失败:', data.error);
            this.isExecuting = false;
            this.isGeneratingStoryboard = false;
            this.$message?.error(data.error?.message || '生成失败');

            // 关闭SSE连接
            if (this.sseClient) {
              this.sseClient.disconnect();
              this.sseClient = null;
            }
          })
          .on('close', () => {
            console.log('[RewriteNode] SSE连接已关闭');
          });

      } catch (error) {
        console.error('执行失败:', error);
        this.$message?.error('执行失败: ' + error.message);
        this.isExecuting = false;
        this.isGeneratingStoryboard = false;

        // 清理SSE连接
        if (this.sseClient) {
          this.sseClient.disconnect();
          this.sseClient = null;
        }
      }
    },

    async handleSave() {
      this.isSaving = true;
      try {
        await this.$emit('save', {
          stageType: 'rewrite',
          outputData: { rewritten_content: this.rewrittenContent }
        });
        this.$message?.success('保存成功');
      } catch (error) {
        this.$message?.error('保存失败');
      } finally {
        this.isSaving = false;
      }
    },

    async handleRetry() {
      await this.handleExecute();
    },

    async handleReset() {
      if (confirm('确定要重新生成吗？这将覆盖当前内容。')) {
        await this.handleExecute();
      }
    },

    formatDate(dateStr) {
      if (!dateStr) return 'N/A';
      return new Date(dateStr).toLocaleString('zh-CN');
    }
  },
  beforeDestroy() {
    // 组件销毁前清理SSE连接
    if (this.sseClient) {
      this.sseClient.disconnect();
      this.sseClient = null;
    }
  }
};
</script>

<style scoped>
.rewrite-node-expanded {
  width: 580px;
  background: #fafafa;
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 1rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 2;
  transition: all 0.3s ease;
}

.rewrite-node-expanded:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

/* 状态样式 */
.status-pending {
  border-color: hsl(var(--bc) / 0.3);
}

.status-processing {
  border-color: hsl(var(--in));
  background: #f0f8ff;
}

.status-completed {
  border-color: hsl(var(--su));
  background: #fafafa;
}

.status-failed {
  border-color: hsl(var(--er));
  background: #fef2f2;
}

/* 节点头部 */
.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.1);
  background: hsl(var(--b2) / 0.5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.node-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: hsl(var(--bc));
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* 操作图标按钮 */
.action-icons {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 0.5rem;
  background: hsl(var(--b2));
  color: hsl(var(--bc));
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-btn:hover:not(.icon-btn-disabled) {
  background: hsl(var(--p));
  color: hsl(var(--pc));
  transform: scale(1.05);
}

.icon-btn:active:not(.icon-btn-disabled) {
  transform: scale(0.95);
}

.icon-btn-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-processing .status-badge {
  background: hsl(var(--in) / 0.1);
  color: hsl(var(--in));
}

.status-completed .status-badge {
  background: hsl(var(--su) / 0.1);
  color: hsl(var(--su));
}

.status-failed .status-badge {
  background: hsl(var(--er) / 0.1);
  color: hsl(var(--er));
}

.status-pending .status-badge {
  background: hsl(var(--bc) / 0.05);
  color: hsl(var(--bc) / 0.6);
}

/* 节点内容区 */
.node-section {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.section-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: hsl(var(--bc) / 0.7);
  margin-bottom: 0.5rem;
}

.original-text {
  padding: 0.75rem;
  background: hsl(var(--b2));
  border-radius: 0.5rem;
  font-size: 0.875rem;
  line-height: 1.6;
  color: hsl(var(--bc) / 0.8);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.original-text::-webkit-scrollbar {
  width: 4px;
}

.original-text::-webkit-scrollbar-thumb {
  background: hsl(var(--bc) / 0.2);
  border-radius: 2px;
}

/* 操作按钮 */
.node-actions {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

/* 元数据 */
.node-metadata {
  padding: 0.75rem 1.25rem;
  display: flex;
  gap: 1.5rem;
  font-size: 0.75rem;
  color: hsl(var(--bc) / 0.5);
}

.metadata-item {
  display: flex;
  gap: 0.5rem;
}

.metadata-label {
  font-weight: 500;
}

.metadata-value {
  color: hsl(var(--bc) / 0.7);
}
</style>
