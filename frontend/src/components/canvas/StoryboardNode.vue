<template>
  <div
    class="storyboard-node"
    :class="`status-${overallStatus}`"
    :style="nodeStyle"
  >
    <!-- 节点头部 -->
    <div class="node-header">
      <div class="header-left">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
        </svg>
        <span class="node-title">分镜 {{ index + 1 }}</span>
      </div>
      <div class="header-actions">
        <span class="duration-badge">{{ storyboard.duration_seconds || 3 }}s</span>
        <button
          class="btn btn-circle btn-xs btn-ghost"
          @click="handleSave"
          title="保存修改"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 场景描述 -->
    <div class="node-section">
      <label class="section-label">场景描述</label>
      <textarea
        v-model="sceneDescription"
        class="textarea textarea-bordered textarea-xs w-full"
        rows="4"
        placeholder="场景描述..."
      ></textarea>
    </div>

    <!-- 旁白文案 -->
    <div class="node-section">
      <label class="section-label">旁白文案</label>
      <textarea
        v-model="narrationText"
        class="textarea textarea-bordered textarea-xs w-full"
        rows="2"
        placeholder="旁白文案..."
      ></textarea>
    </div>

  </div>
</template>

<script>
export default {
  name: 'StoryboardNode',
  props: {
    storyboard: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    position: {
      type: Object,
      default: () => ({ x: 0, y: 0 })
    }
  },
  data() {
    return {
      sceneDescription: this.storyboard.generation_metadata.raw_scene_data.visual_prompt || '',
      narrationText: this.storyboard.generation_metadata.raw_scene_data.narration || ''
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
    overallStatus() {
      // 根据关联的图片、运镜、视频状态判断
      if (this.storyboard.videos && this.storyboard.videos.length > 0) {
        return 'completed';
      } else if (this.storyboard.images && this.storyboard.images.length > 0) {
        return 'processing';
      }
      return 'pending';
    }
  },
  methods: {
    handleSave() {
      this.$emit('save', {
        storyboardId: this.storyboard.id,
        data: {
          scene_description: this.sceneDescription,
          narration_text: this.narrationText
        }
      });
    }
  }
};
</script>

<style scoped>
.storyboard-node {
  width: 280px;
  background: #fafafa;
  border: 2px solid hsl(var(--bc) / 0.2);
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 2;
  transition: all 0.3s ease;
}

.storyboard-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-pending {
  border-color: hsl(var(--bc) / 0.2);
  background: #fafafa;
}

.status-processing {
  border-color: hsl(var(--wa));
  background: #fffbeb;
}

.status-completed {
  border-color: hsl(var(--su));
  background: #f0fdf4;
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
  gap: 0.5rem;
}

.duration-badge {
  font-size: 0.6875rem;
  padding: 0.25rem 0.5rem;
  background: hsl(var(--bc) / 0.1);
  border-radius: 0.375rem;
  color: hsl(var(--bc) / 0.7);
}

.node-section {
  padding: 0.75rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.section-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--bc) / 0.6);
  margin-bottom: 0.375rem;
}

</style>
