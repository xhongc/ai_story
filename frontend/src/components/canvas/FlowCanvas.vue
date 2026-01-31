<template>
  <div class="flow-canvas-wrapper" ref="wrapper">
    <!-- 画布控制工具栏 -->
    <div class="canvas-controls">
      <div class="btn-group">
        <button class="btn btn-sm btn-ghost" @click="zoomIn" title="放大">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
          </svg>
        </button>
        <button class="btn btn-sm btn-ghost" @click="zoomOut" title="缩小">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM7 10h6" />
          </svg>
        </button>
        <button class="btn btn-sm btn-ghost" @click="resetView" title="适应画布">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>
      <div class="text-xs text-base-content/60 ml-2">
        {{ Math.round(scale * 100) }}%
      </div>
    </div>

    <!-- 画布容器 -->
    <div
      class="canvas-container"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @wheel="handleWheel"
    >
      <!-- 可变换的画布内容 -->
      <div
        class="canvas-content"
        :style="canvasStyle"
      >
        <!-- 节点内容插槽 -->
        <slot :scale="scale"></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FlowCanvas',
  props: {
    nodes: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      scale: 1,
      translateX: 0,
      translateY: 0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      startTranslateX: 0,
      startTranslateY: 0,
      minScale: 0.3,
      maxScale: 2,
    };
  },
  computed: {
    canvasStyle() {
      return {
        transform: `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`,
        transformOrigin: '0 0',
      };
    }
  },
  mounted() {
    // 初始化视图：自动适配所有节点
    this.$nextTick(() => {
      this.fitAllNodes();
    });
  },
  watch: {
    // 监听节点变化，自动适配
    nodes: {
      deep: true,
      handler() {
        this.$nextTick(() => {
          this.fitAllNodes();
        });
      }
    }
  },
  methods: {
    // 缩放控制
    zoomIn() {
      this.setScale(this.scale * 1.2);
    },
    zoomOut() {
      this.setScale(this.scale / 1.2);
    },
    setScale(newScale) {
      this.scale = Math.max(this.minScale, Math.min(this.maxScale, newScale));
    },
    resetView() {
      this.fitAllNodes();
    },

    // 自动适配所有节点
    fitAllNodes() {
      const wrapper = this.$refs.wrapper;
      if (!wrapper || Object.keys(this.nodes).length === 0) {
        // 如果没有节点，使用默认居中
        this.centerView();
        return;
      }

      // 计算所有节点的边界
      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;

      Object.values(this.nodes).forEach(node => {
        minX = Math.min(minX, node.x);
        minY = Math.min(minY, node.y);
        maxX = Math.max(maxX, node.x + (node.width || 200));
        maxY = Math.max(maxY, node.y + (node.height || 100));
      });

      // 计算内容的宽高
      const contentWidth = maxX - minX;
      const contentHeight = maxY - minY;

      // 计算容器的宽高
      const containerWidth = wrapper.clientWidth;
      const containerHeight = wrapper.clientHeight;

      // 计算合适的缩放比例（留出边距）
      const padding = 50; // 边距
      const scaleX = (containerWidth - padding * 2) / contentWidth;
      const scaleY = (containerHeight - padding * 2) / contentHeight;
      const targetScale = Math.min(scaleX, scaleY, 1); // 不超过1倍

      // 设置缩放
      this.scale = Math.max(this.minScale, Math.min(this.maxScale, targetScale));

      // 计算平移，使内容居中
      const scaledContentWidth = contentWidth * this.scale;
      const scaledContentHeight = contentHeight * this.scale;

      this.translateX = (containerWidth - scaledContentWidth) / 2 - minX * this.scale;
      this.translateY = (containerHeight - scaledContentHeight) / 2 - minY * this.scale;
    },

    centerView() {
      // 将画布内容居中显示（默认行为）
      const wrapper = this.$refs.wrapper;
      if (wrapper) {
        this.translateX = wrapper.clientWidth / 2 - 200;
        this.translateY = 100;
        this.scale = 1;
      }
    },

    // 鼠标拖动
    handleMouseDown(e) {
      // 只有在空白区域点击才开始拖动
      if (e.target.classList.contains('canvas-container') ||
          e.target.classList.contains('canvas-content')) {
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        this.startTranslateX = this.translateX;
        this.startTranslateY = this.translateY;
        e.preventDefault();
      }
    },
    handleMouseMove(e) {
      if (this.isDragging) {
        const dx = e.clientX - this.dragStartX;
        const dy = e.clientY - this.dragStartY;
        this.translateX = this.startTranslateX + dx;
        this.translateY = this.startTranslateY + dy;
      }
    },
    handleMouseUp() {
      this.isDragging = false;
    },

    // 鼠标滚轮缩放
    handleWheel(e) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.98 : 1.02;
      this.setScale(this.scale * delta);
    }
  }
};
</script>

<style scoped>
.flow-canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 600px;
  background: hsl(var(--b2));
  border-radius: 0.5rem;
  overflow: hidden;
}

.canvas-controls {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: hsl(var(--b1));
  padding: 0.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.canvas-container {
  width: 100%;
  height: 100%;
  cursor: grab;
  position: relative;
  overflow: hidden;
  /* 网格线背景 */
  background-color: #f5f5f5;
  background-image:
    linear-gradient(#e0e0e0 1px, transparent 1px),
    linear-gradient(90deg, #e0e0e0 1px, transparent 1px);
  background-size: 20px 20px;
}

.canvas-container:active {
  cursor: grabbing;
}

.canvas-content {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.1s ease-out;
}

</style>
