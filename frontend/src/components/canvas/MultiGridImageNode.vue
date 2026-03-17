<template>
  <div
    class="multi-grid-node"
    :class="`status-${status}`"
    :style="nodeStyle"
    @dblclick="handleNodeDoubleClick"
  >
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4h7v7H4V4zm9 0h7v7h-7V4zM4 13h7v7H4v-7zm9 0h7v7h-7v-7z" />
        </svg>
        <span class="node-title">多宫格图片</span>
      </div>
      <div class="header-actions">
        <span v-if="status === 'processing'" class="loading loading-spinner loading-xs" />
        <svg
          v-else-if="status === 'completed'"
          xmlns="http://www.w3.org/2000/svg"
          class="h-3 w-3 text-success"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <button
          v-if="status === 'pending' || status === 'failed'"
          class="btn btn-circle btn-xs btn-primary"
          :disabled="isGenerating"
          title="生成多宫格图片"
          @click="handleGenerate"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>
        <button
          v-if="status === 'completed'"
          class="btn btn-circle btn-xs btn-ghost"
          title="重新生成"
          @click="handleRegenerate"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <div class="node-body">
      <div class="source-preview">
        <img
          v-if="sourceImageUrl"
          :src="sourceImageUrl"
          alt="多宫格源图"
          class="preview-img"
          @load="handleImageLoad"
        >
        <div v-else class="image-placeholder">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      <div class="node-meta">
        <span>{{ gridLabel }}</span>
        <span>{{ tileCount }} 张切片</span>
      </div>

      <div class="tile-grid" :style="tileGridStyle">
        <div v-for="tile in previewTiles" :key="tile.id || tile.tile_index" class="tile-card">
          <img :src="tile.tile_image_url" :alt="`切片${tile.tile_index}`" class="tile-img">
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MultiGridImageNode',
  props: {
    status: { type: String, default: 'pending' },
    position: { type: Object, default: () => ({ x: 0, y: 0 }) },
    sourceImageUrl: { type: String, default: '' },
    tasks: { type: Array, default: () => [] },
    storyboardId: { type: [String, Number], required: true },
    mediaWidth: { type: Number, default: 1080 },
    mediaHeight: { type: Number, default: 1080 }
  },
  data() {
    return { isGenerating: false };
  },
  computed: {
    latestTask() {
      return this.tasks[0] || null;
    },
    previewTiles() {
      return (this.latestTask?.tiles || []).slice(0, 4);
    },
    tileCount() {
      return (this.latestTask?.tiles || []).length;
    },
    gridLabel() {
      const rows = this.latestTask?.grid_rows || 2;
      const cols = this.latestTask?.grid_cols || 2;
      return `${rows} × ${cols}`;
    },
    previewHeight() {
      const safeWidth = this.mediaWidth > 0 ? this.mediaWidth : 1;
      const safeHeight = this.mediaHeight > 0 ? this.mediaHeight : 1;
      const previewHeight = 180 * (safeHeight / safeWidth);
      return Math.max(120, Math.round(previewHeight));
    },
    nodeStyle() {
      return {
        position: 'absolute',
        left: `${this.position.x}px`,
        top: `${this.position.y}px`,
        '--media-preview-height': `${this.previewHeight}px`
      };
    },
    tileGridStyle() {
      const cols = Math.min(Math.max(this.latestTask?.grid_cols || 2, 2), 4);
      return { gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` };
    }
  },
  methods: {
    handleNodeDoubleClick(event) {
      if (!(event.target instanceof Element)) {
        this.$emit('node-dblclick');
        return;
      }
      if (event.target.closest('button, input, textarea, select, option, video, [contenteditable="true"], .prevent-canvas-wheel')) {
        return;
      }
      this.$emit('node-dblclick');
    },
    handleImageLoad(event) {
      const target = event?.target;
      const width = Number(target?.naturalWidth);
      const height = Number(target?.naturalHeight);
      if (width > 0 && height > 0) {
        this.$emit('media-loaded', { storyboardId: this.storyboardId, width, height });
      }
    },
    async handleGenerate(forceRegenerate = false) {
      this.isGenerating = true;
      try {
        this.$emit('generate', { storyboardId: this.storyboardId, forceRegenerate });
      } finally {
        this.isGenerating = false;
      }
    },
    async handleRegenerate() {
      const confirmed = await this.$confirm('确定要重新生成多宫格图片吗？', '重新生成多宫格图片', { tone: 'warning', confirmText: '重新生成' });
      if (confirmed) {
        await this.handleGenerate(true);
      }
    }
  }
};
</script>

<style scoped>
.multi-grid-node {
  width: 250px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.multi-grid-node:hover {
  transform: translateY(-4px);
  box-shadow: 0 24px 48px rgba(14, 165, 233, 0.16);
  border-color: rgba(14, 165, 233, 0.28);
}

.layout-shell.theme-dark .multi-grid-node {
  background: rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 20px 44px rgba(2, 6, 23, 0.45);
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 0.9rem;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.88));
}

.layout-shell.theme-dark .node-header {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.9));
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.node-body {
  padding: 0.8rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.source-preview {
  height: var(--media-preview-height);
  border-radius: 14px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.12);
}

.preview-img,
.tile-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
}

.layout-shell.theme-dark .node-meta {
  color: #cbd5e1;
}

.tile-grid {
  display: grid;
  gap: 0.4rem;
}

.tile-card {
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
  background: rgba(148, 163, 184, 0.12);
}
</style>
