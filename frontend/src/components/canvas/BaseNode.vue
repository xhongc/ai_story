<template>
  <div
    class="flow-node"
    :class="[
      `status-${status}`,
      { 'node-clickable': clickable }
    ]"
    :style="nodeStyle"
    @click="handleClick"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="node-icon">
        <slot name="icon">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </slot>
      </div>
      <div class="node-title">{{ title }}</div>
      <div class="node-status-indicator">
        <span v-if="status === 'processing'" class="loading loading-spinner loading-xs"></span>
        <svg v-else-if="status === 'completed'" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <svg v-else-if="status === 'failed'" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
    </div>

    <!-- 节点内容 -->
    <div class="node-body">
      <slot></slot>
    </div>

    <!-- 节点底部（可选） -->
    <div v-if="$slots.footer" class="node-footer">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BaseNode',
  props: {
    title: {
      type: String,
      required: true
    },
    status: {
      type: String,
      default: 'pending',
      validator: (value) => ['pending', 'processing', 'completed', 'failed'].includes(value)
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    width: {
      type: Number,
      default: 280
    },
    clickable: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    nodeStyle() {
      return {
        position: 'absolute',
        left: `${this.position.x}px`,
        top: `${this.position.y}px`,
        width: `${this.width}px`,
      };
    }
  },
  methods: {
    handleClick() {
      if (this.clickable) {
        this.$emit('click');
      }
    }
  }
};
</script>

<style scoped>
.flow-node {
  background: #fafafa;
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  z-index: 2;
}

.flow-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.node-clickable {
  cursor: pointer;
}

.node-clickable:hover {
  transform: translateY(-2px);
}

/* 状态样式 */
.status-pending {
  border-color: hsl(var(--bc) / 0.2);
  background: #fafafa;
}

.status-processing {
  border-color: hsl(var(--in));
  background: #f0f8ff;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.status-completed {
  border-color: hsl(var(--su));
  background: #f0fdf4;
}

.status-failed {
  border-color: hsl(var(--er));
  background: #fef2f2;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

/* 节点头部 */
.node-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.1);
}

.node-icon {
  flex-shrink: 0;
  color: hsl(var(--bc) / 0.6);
}

.node-title {
  flex: 1;
  font-weight: 600;
  font-size: 0.875rem;
  color: hsl(var(--bc));
}

.node-status-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
}

.status-processing .node-status-indicator {
  color: hsl(var(--in));
}

.status-completed .node-status-indicator {
  color: hsl(var(--su));
}

.status-failed .node-status-indicator {
  color: hsl(var(--er));
}

/* 节点内容 */
.node-body {
  padding: 1rem;
  font-size: 0.875rem;
  color: hsl(var(--bc) / 0.8);
  max-height: 200px;
  overflow-y: auto;
}

.node-body::-webkit-scrollbar {
  width: 4px;
}

.node-body::-webkit-scrollbar-thumb {
  background: hsl(var(--bc) / 0.2);
  border-radius: 2px;
}

/* 节点底部 */
.node-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid hsl(var(--bc) / 0.1);
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
</style>
