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
      <select
        v-model="localMovementType"
        class="select select-bordered select-xs w-full"
        :disabled="status === 'processing'"
      >
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
      </select>
    </div>

    <!-- 运镜参数 -->
    <div v-if="status === 'completed' && movementParams" class="node-info">
      <div class="info-item">
        <span class="info-label">速度:</span>
        <span class="info-value">{{ movementParams.speed || 'N/A' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">强度:</span>
        <span class="info-value">{{ movementParams.intensity || 'N/A' }}</span>
      </div>
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
    canGenerate: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      localMovementType: this.movementType,
      isGenerating: false
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

.camera-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-pending {
  border-color: hsl(var(--bc) / 0.2);
  background: #fafafa;
}

.status-processing {
  border-color: hsl(var(--in));
  background: #f0f8ff;
}

.status-completed {
  border-color: hsl(var(--su));
  background: #f0fdf4;
}

.status-failed {
  border-color: hsl(var(--er));
  background: #fef2f2;
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.1);
  background: hsl(var(--b2) / 0.3);
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

.content-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--bc) / 0.6);
  margin-bottom: 0.375rem;
}

.node-info {
  padding: 0.625rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.6875rem;
}

.info-label {
  color: hsl(var(--bc) / 0.5);
}

.info-value {
  color: hsl(var(--bc) / 0.8);
  font-weight: 500;
}

</style>
