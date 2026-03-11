<template>
  <div
    class="rewrite-node-expanded"
    :class="`status-${effectiveStatus}`"
    :style="nodeStyle"
  >
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        <h3 class="node-title">文案改写</h3>
      </div>
      <div class="header-right">
        <div class="action-icons">
          <button
            class="icon-btn"
            :class="{ 'icon-btn-disabled': status === 'processing' || isExecuting || isGeneratingStoryboard }"
            :disabled="status === 'processing' || isExecuting || isGeneratingStoryboard"
            title="运行改写"
            @click.stop="handleQuickExecute('rewrite')"
          >
            <span v-if="isExecuting && !isGeneratingStoryboard" class="loading loading-spinner loading-xs"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>

          <button
            class="icon-btn"
            :class="{ 'icon-btn-disabled': status === 'processing' || isGeneratingStoryboard || isExecuting }"
            :disabled="status === 'processing' || isGeneratingStoryboard || isExecuting"
            title="生成分镜"
            @click.stop="handleGenerateStoryboard('storyboard')"
          >
            <span v-if="isGeneratingStoryboard" class="loading loading-spinner loading-xs"></span>
            <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div class="node-section">
      <label class="section-label">原始文案</label>
      <div
        class="original-text"
        @wheel.stop
        @mousedown.stop
      >{{ data.original_text || '暂无原始文案' }}</div>
    </div>

    <div class="node-section">
      <label class="section-label">改写后文案</label>
      <div class="textarea-autocomplete-wrap">
        <textarea
          ref="rewriteTextarea"
          v-model="localText"
          class="textarea textarea-bordered w-full"
          rows="8"
          placeholder="改写后的文案将显示在这里..."
          :disabled="status === 'processing'"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleTextInput"
          @click="handleCursorChange"
          @keyup="handleCursorChange"
          @keydown.down.prevent="navigateAutocomplete(1)"
          @keydown.up.prevent="navigateAutocomplete(-1)"
          @keydown.enter.exact.prevent="confirmAutocomplete"
          @keydown.esc.prevent="closeAutocomplete"
          @wheel.stop
          @mousedown.stop
        ></textarea>
        <div v-if="showAutocomplete && filteredAssetOptions.length" class="asset-autocomplete prevent-canvas-wheel">
          <button
            v-for="(asset, index) in filteredAssetOptions"
            :key="asset.id"
            type="button"
            class="asset-autocomplete-item"
            :class="{ active: highlightedAssetIndex === index }"
            @mousedown.prevent="selectAutocomplete(asset.key)"
          >
            <code>{{ asset.key }}</code>
            <span>{{ asset.group || asset.variable_type_display }}</span>
          </button>
        </div>
      </div>
    </div>

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
    assetOptions: {
      type: Array,
      default: () => []
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
      isExecuting: false,
      isSaving: false,
      isGeneratingStoryboard: false,
      sseClient: null,
      streamingText: '',
      localText: this.data?.rewritten_text || '',
      lastSavedText: '',
      isEditing: false,
      showAutocomplete: false,
      autocompleteStart: -1,
      autocompleteQuery: '',
      highlightedAssetIndex: 0,
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
    },
    filteredAssetOptions() {
      const keyword = this.autocompleteQuery.trim().toLowerCase();
      if (!keyword) {
        return this.assetOptions;
      }
      return this.assetOptions.filter((asset) => {
        const key = (asset.key || '').toLowerCase();
        const group = (asset.group || '').toLowerCase();
        return key.includes(keyword) || group.includes(keyword);
      });
    }
  },
  watch: {
    'data.rewritten_text': {
      immediate: true,
      handler(newVal) {
        if (!this.isEditing) {
          this.localText = newVal || '';
          this.lastSavedText = newVal || '';
        }
      }
    },
    assetOptions() {
      if (this.highlightedAssetIndex >= this.filteredAssetOptions.length) {
        this.highlightedAssetIndex = 0;
      }
    }
  },
  methods: {
    handleFocus() {
      this.isEditing = true;
    },
    handleBlur() {
      this.isEditing = false;
      this.handleAutoSave();
      setTimeout(() => {
        this.closeAutocomplete();
      }, 120);
    },
    handleTextInput(event) {
      this.updateAutocomplete(event.target);
    },
    handleCursorChange() {
      this.updateAutocomplete(this.$refs.rewriteTextarea);
    },
    updateAutocomplete(textarea) {
      if (!textarea) {
        return;
      }
      const cursor = textarea.selectionStart || 0;
      const textBeforeCursor = this.localText.slice(0, cursor);
      const openIndex = textBeforeCursor.lastIndexOf('{{');
      const closeIndex = textBeforeCursor.lastIndexOf('}}');
      if (openIndex === -1 || closeIndex > openIndex) {
        this.closeAutocomplete();
        return;
      }

      const rawQuery = textBeforeCursor.slice(openIndex + 2);
      if (/[^\sa-zA-Z0-9_]/.test(rawQuery)) {
        this.closeAutocomplete();
        return;
      }

      this.autocompleteStart = openIndex;
      this.autocompleteQuery = rawQuery.trimStart();
      this.highlightedAssetIndex = 0;
      this.showAutocomplete = this.assetOptions.length > 0;
    },
    closeAutocomplete() {
      this.showAutocomplete = false;
      this.autocompleteStart = -1;
      this.autocompleteQuery = '';
      this.highlightedAssetIndex = 0;
    },
    navigateAutocomplete(step) {
      if (!this.showAutocomplete || !this.filteredAssetOptions.length) {
        return;
      }
      const total = this.filteredAssetOptions.length;
      this.highlightedAssetIndex = (this.highlightedAssetIndex + step + total) % total;
    },
    confirmAutocomplete() {
      if (!this.showAutocomplete || !this.filteredAssetOptions.length) {
        return;
      }
      const target = this.filteredAssetOptions[this.highlightedAssetIndex];
      if (target) {
        this.selectAutocomplete(target.key);
      }
    },
    selectAutocomplete(assetKey) {
      const textarea = this.$refs.rewriteTextarea;
      if (!textarea || this.autocompleteStart === -1) {
        return;
      }
      const cursor = textarea.selectionStart || 0;
      const token = `{{ ${assetKey} }}`;
      const nextValue = `${this.localText.slice(0, this.autocompleteStart)}${token}${this.localText.slice(cursor)}`;
      this.localText = nextValue;
      this.closeAutocomplete();
      this.$nextTick(() => {
        const nextCursor = this.autocompleteStart + token.length;
        textarea.focus();
        textarea.setSelectionRange(nextCursor, nextCursor);
      });
      this.handleAutoSave();
    },
    handleAutoSave() {
      if (this.status === 'processing') {
        return;
      }
      const nextText = this.localText || '';
      if (nextText === this.lastSavedText) {
        return;
      }
      this.$emit('save', {
        stageType: 'rewrite',
        outputData: { rewritten_text: nextText },
        silent: true
      });
      this.lastSavedText = nextText;
    },
    async handleQuickExecute(mode = 'rewrite') {
      if (this.status === 'processing' || this.isExecuting) {
        return;
      }
      await this.handleExecute(mode);
    },
    async handleGenerateStoryboard(mode = 'storyboard') {
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
      this.streamingText = '';

      try {
        await projectsAPI.executeStage(
          this.projectId,
          mode,
          { original_topic: this.originalTopic },
          true
        );

        if (this.sseClient) {
          this.sseClient.disconnect();
          this.sseClient = null;
        }

        this.sseClient = createProjectStageSSE(this.projectId, mode, {
          autoReconnect: false
        });

        this.sseClient
          .on('open', () => {
            console.log('[RewriteNode] SSE连接已建立');
          })
          .on('token', (data) => {
            if (data.content) {
              this.streamingText += data.content;
              this.localText = this.streamingText;
            }
          })
          .on('done', (data) => {
            console.log('[RewriteNode] 生成完成, mode:', mode);
            this.isExecuting = false;
            this.isGeneratingStoryboard = false;

            if (data.full_text) {
              this.streamingText = data.full_text;
              this.localText = this.streamingText;
            }

            if (mode === 'storyboard') {
              this.$message?.success('分镜生成完成');
              this.$emit('storyboard-generated');
            } else {
              this.$message?.success('文案改写完成');
            }

            if (this.sseClient) {
              this.sseClient.disconnect();
              this.sseClient = null;
            }
          })
          .on('error', (data) => {
            console.error('[RewriteNode] 生成失败:', data.error);
            this.isExecuting = false;
            this.isGeneratingStoryboard = false;
            this.$message?.error(data.error?.message || '生成失败');

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
          outputData: { rewritten_text: this.localText || '' },
          silent: false
        });
        this.$message?.success('保存成功');
        this.lastSavedText = this.localText || '';
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

.layout-shell.theme-dark .rewrite-node-expanded {
  background: #0f172a;
  border-color: hsl(var(--bc) / 0.28);
  box-shadow: 0 6px 20px rgba(2, 6, 23, 0.6);
}

.rewrite-node-expanded:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.layout-shell.theme-dark .rewrite-node-expanded:hover {
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.75);
}

.status-pending {
  border-color: hsl(var(--bc) / 0.3);
}

.status-processing {
  border-color: hsl(var(--in));
  background: #f0f8ff;
}

.layout-shell.theme-dark .status-processing {
  background: rgba(14, 116, 144, 0.2);
}

.status-completed {
  border-color: hsl(var(--su));
  background: #fafafa;
}

.layout-shell.theme-dark .status-completed {
  background: #0f172a;
}

.status-failed {
  border-color: hsl(var(--er));
  background: #fef2f2;
}

.layout-shell.theme-dark .status-failed {
  background: rgba(127, 29, 29, 0.2);
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.1);
  background: hsl(var(--b2) / 0.5);
}

.layout-shell.theme-dark .node-header {
  border-bottom-color: hsl(var(--bc) / 0.2);
  background: hsl(var(--b2) / 0.6);
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

.layout-shell.theme-dark .icon-btn {
  background: hsl(var(--b2) / 0.85);
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

.node-section {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.layout-shell.theme-dark .node-section {
  border-bottom-color: hsl(var(--bc) / 0.15);
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

.layout-shell.theme-dark .original-text {
  background: hsl(var(--b2) / 0.85);
}

.original-text::-webkit-scrollbar {
  width: 4px;
}

.original-text::-webkit-scrollbar-thumb {
  background: hsl(var(--bc) / 0.2);
  border-radius: 2px;
}

.layout-shell.theme-dark .original-text::-webkit-scrollbar-thumb {
  background: hsl(var(--bc) / 0.3);
}

.textarea-autocomplete-wrap {
  position: relative;
}

.asset-autocomplete {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0.75rem;
  display: grid;
  gap: 0.45rem;
  max-height: 220px;
  overflow-y: auto;
  padding: 0.7rem;
  border-radius: 1rem;
  border: 1px solid hsl(var(--bc) / 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(10px);
  z-index: 20;
}

.layout-shell.theme-dark .asset-autocomplete {
  background: rgba(15, 23, 42, 0.96);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.62);
}

.asset-autocomplete-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.85rem;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.72);
  color: hsl(var(--bc));
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .asset-autocomplete-item {
  background: rgba(15, 23, 42, 0.85);
}

.asset-autocomplete-item:hover,
.asset-autocomplete-item.active {
  border-color: rgba(14, 165, 233, 0.28);
  transform: translateY(-1px);
}

.node-actions {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

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
