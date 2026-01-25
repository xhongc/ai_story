<template>
  <div
    class="image-gen-node"
    :class="`status-${status}`"
    :style="nodeStyle"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span class="node-title">文生图</span>
      </div>
      <div class="header-actions">
        <span v-if="status === 'processing'" class="loading loading-spinner loading-xs"></span>
        <svg v-else-if="status === 'completed'" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <button
          v-if="status === 'pending' || status === 'failed'"
          class="btn btn-circle btn-xs btn-primary"
          :disabled="isGenerating"
          @click="handleGenerate"
          title="生成图片"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
        <button
          v-if="status === 'completed'"
          class="btn btn-circle btn-xs btn-ghost"
          @click="handleRegenerate"
          title="重新生成"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 图片预览 -->
    <div v-if="status === 'completed' && imageUrl" class="image-preview">
      <img :src="imageUrl" alt="生成的图片" class="preview-img" />
    </div>

    <!-- 提示词 -->
    <div class="node-content">
      <label class="content-label">提示词</label>
      <textarea
        v-model="localPrompt"
        class="textarea textarea-bordered textarea-xs w-full"
        rows="2"
        placeholder="文生图提示词..."
        :disabled="status === 'processing'"
      ></textarea>
    </div>

  </div>
</template>

<script>
export default {
  name: 'ImageGenNode',
  props: {
    status: {
      type: String,
      default: 'pending'
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    imageUrl: {
      type: String,
      default: ''
    },
    prompt: {
      type: String,
      default: ''
    },
    storyboardId: {
      type: [String, Number],
      required: true
    }
  },
  data() {
    return {
      localPrompt: this.prompt,
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
    prompt(newVal) {
      this.localPrompt = newVal;
    }
  },
  methods: {
    async handleGenerate() {
      this.isGenerating = true;
      try {
        await this.$emit('generate', {
          storyboardId: this.storyboardId,
          prompt: this.localPrompt
        });
      } finally {
        this.isGenerating = false;
      }
    },
    async handleRegenerate() {
      if (confirm('确定要重新生成图片吗？')) {
        await this.handleGenerate();
      }
    }
  }
};
</script>

<style scoped>
.image-gen-node {
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

.image-gen-node:hover {
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

.image-preview {
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: hsl(var(--b3));
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

</style>
