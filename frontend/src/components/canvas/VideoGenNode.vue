<template>
  <div
    class="video-gen-node"
    :class="`status-${status}`"
    :style="nodeStyle"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="node-title">图生视频</span>
      </div>
      <div class="header-actions">
        <span v-if="status === 'processing'" class="loading loading-spinner loading-xs"></span>
        <svg v-else-if="status === 'completed'" xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
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
        <button
          v-else
          class="btn btn-circle btn-xs btn-primary"
          @click="handleGenerate"
          title="生成视频"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 视频预览 -->
    <div v-if="videoUrl" class="video-preview">
      <video :src="videoUrl" class="preview-video" controls></video>
    </div>

  </div>
</template>

<script>
export default {
  name: 'VideoGenNode',
  props: {
    status: {
      type: String,
      default: 'pending'
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    },
    videoUrl: {
      type: String,
      default: ''
    },
    videoInfo: {
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
  methods: {
    async handleGenerate() {

      this.isGenerating = true;
      try {
        this.$emit('generate', {
          storyboardId: this.storyboardId
        });
      } catch (error) {
        console.error('[VideoGenNode] 生成失败:', error);
        this.$message?.error(error.message || '生成视频失败');
      } finally {
        this.isGenerating = false;
      }
    },
    async handleRegenerate() {
      if (confirm('确定要重新生成视频吗？')) {
        await this.handleGenerate();
      }
    }
  }
};
</script>

<style scoped>
.video-gen-node {
  width: 250px;
  height: 280px;
  background: #fafafa;
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 2;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.video-gen-node:hover {
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
  background: #fafafa;
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

.video-preview {
  flex: 1;
  width: 100%;
  overflow: hidden;
  background: hsl(var(--b3));
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

</style>
