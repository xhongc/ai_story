<template>
  <div
    class="camera-node"
    :class="`status-${status}`"
    :style="nodeStyle"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <span class="node-title">运镜</span>
      </div>
      <div class="header-actions">
        <span v-if="status === 'processing'" class="loading loading-spinner loading-xs"></span>
        <svg v-else-if="status === 'completed'" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <button
          class="btn btn-circle btn-xs btn-primary"
          @click="handleGenerate"
          title="生成运镜"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 运镜类型 -->
    <div class="node-content">
      <label class="content-label">运镜类型</label>
      <input
        v-model="localMovementType"
        list="movement-type-options"
        class="input input-bordered input-xs w-full input-sm"
        :disabled="status === 'processing'"
        placeholder="自动选择或输入自定义类型"
        @blur="handleMovementTypeChange"
      />
      <datalist id="movement-type-options">
        <option value="">自动选择</option>
        <option value="static">静态</option>
        <option value="zoom_in">推进</option>
        <option value="zoom_out">拉远</option>
        <option value="pan_left">左移</option>
        <option value="pan_right">右移</option>
        <option value="tilt_up">上摇</option>
        <option value="tilt_down">下摇</option>
        <option value="dolly_in">前推</option>
        <option value="dolly_out">后拉</option>
      </datalist>
    </div>

    <!-- 运镜参数 -->
    <div v-if="status === 'completed' && movementParams" class="node-description">
      <label class="content-label">运镜参数</label>
      <textarea
        v-model="localDescription"
        class="description-textarea"
        :disabled="status === 'processing'"
        placeholder="输入运镜参数描述"
        rows="3"
        @blur="handleDescriptionChange"
      ></textarea>
    </div>

  </div>
</template>

<script>
export default {
  name: 'CameraNode',
  props: {
    status: {
      type: String,
      default: 'pending'
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    movementType: {
      type: String,
      default: ''
    },
    movementParams: {
      type: Object,
      default: null
    },
    storyboardId: {
      type: [String, Number],
      required: true
    },
    cameraId: {
      type: [String, Number],
      default: null
    },
    canGenerate: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      localMovementType: this.movementType,
      localDescription: this.movementParams?.description || '',
      isGenerating: false,
      lastSavedMovementType: this.movementType,
      lastSavedDescription: this.movementParams?.description || ''
    };
  },
  computed: {
    nodeStyle() {
      return {
        position: 'absolute',
        left: `${this.position.x}px`,
        top: `${this.position.y}px`,
      };
    }
  },
  watch: {
    movementType(newVal) {
      this.localMovementType = newVal;
      this.lastSavedMovementType = newVal;
    },
    movementParams: {
      handler(newVal) {
        if (newVal?.description !== undefined) {
          this.localDescription = newVal.description;
          this.lastSavedDescription = newVal.description;
        }
      },
      deep: true
    }
  },
  methods: {
    async handleGenerate() {
      this.isGenerating = true;
      try {
        this.$emit('generate', {
          storyboardId: this.storyboardId,
          movementType: this.localMovementType
        });
      } catch (error) {
        console.error('[CameraNode] 生成失败:', error);
        this.$message?.error(error.message || '生成运镜失败');
      } finally {
        this.isGenerating = false;
      }
    },
    async handleRegenerate() {
      await this.handleGenerate();
    },
    handleMovementTypeChange() {
      // 当用户修改运镜类型时，自动保存
      this.handleAutoSave();
    },
    handleDescriptionChange() {
      // 当用户修改运镜描述时，自动保存
      this.handleAutoSave();
    },
    handleAutoSave() {
      // 检查是否有变化
      const movementTypeChanged = this.localMovementType !== this.lastSavedMovementType;
      const descriptionChanged = this.localDescription !== this.lastSavedDescription;

      if (!movementTypeChanged && !descriptionChanged) {
        return;
      }

      // 如果没有 cameraId，说明运镜还未生成，不需要保存
      if (!this.cameraId) {
        return;
      }

      // 构建更新数据
      const data = {};
      if (movementTypeChanged) {
        data.movement_type = this.localMovementType;
      }
      if (descriptionChanged) {
        data.movement_params = {
          ...this.movementParams,
          description: this.localDescription
        };
      }

      // 触发保存事件
      this.$emit('save', {
        cameraId: this.cameraId,
        data,
        silent: true
      });

      // 更新最后保存的值
      this.lastSavedMovementType = this.localMovementType;
      this.lastSavedDescription = this.localDescription;
    }
  }
};
</script>

<style scoped>
.camera-node {
  width: 250px;
  min-height: 280px;
  background: #fafafa;
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 2;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.layout-shell.theme-dark .camera-node {
  background: #0f172a;
  border-color: hsl(var(--bc) / 0.28);
  box-shadow: 0 4px 16px rgba(2, 6, 23, 0.6);
}

.camera-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.layout-shell.theme-dark .camera-node:hover {
  box-shadow: 0 6px 18px rgba(2, 6, 23, 0.75);
}

.status-pending {
  border-color: hsl(var(--bc) / 0.2);
  background: #fafafa;
}

.layout-shell.theme-dark .status-pending {
  background: #0f172a;
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
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.1);
  background: hsl(var(--b2) / 0.3);
}

.layout-shell.theme-dark .node-header {
  border-bottom-color: hsl(var(--bc) / 0.2);
  background: hsl(var(--b2) / 0.45);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.node-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--bc));
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.status-processing .header-actions {
  color: hsl(var(--in));
}

.status-completed .header-actions {
  color: hsl(var(--su));
}

.node-content {
  padding: 0.75rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.layout-shell.theme-dark .node-content {
  border-bottom-color: hsl(var(--bc) / 0.15);
}

.content-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--bc) / 0.6);
  margin-bottom: 0.375rem;
}

.node-description {
  padding: 0.75rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.layout-shell.theme-dark .node-description {
  border-bottom-color: hsl(var(--bc) / 0.15);
}

.description-textarea {
  font-size: 0.75rem;
  line-height: 1.5;
  color: hsl(var(--bc) / 0.7);
  background: hsl(var(--b2) / 0.3);
  padding: 0.625rem;
  border-radius: 0.375rem;
  border: 1px solid hsl(var(--bc) / 0.1);
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  width: 100%;
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
  transition: border-color 0.2s ease;
}

.layout-shell.theme-dark .description-textarea {
  background: hsl(var(--b2) / 0.6);
  border-color: hsl(var(--bc) / 0.2);
  color: hsl(var(--bc) / 0.8);
}

.description-textarea:focus {
  outline: none;
  border-color: hsl(var(--p));
  background: hsl(var(--b1));
}

.layout-shell.theme-dark .description-textarea:focus {
  background: hsl(var(--b2));
}

.description-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

</style>
