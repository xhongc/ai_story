<template>
  <div
    class="storyboard-node"
    :class="`status-${overallStatus}`"
    :style="nodeStyle"
  >
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
          title="保存修改"
          @click="handleSave"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <div class="node-section node-section-compact">
      <label class="section-label">场景</label>
      <input
        v-model="sceneDescription"
        type="text"
        class="input input-bordered input-xs flex-1 input-sm"
        placeholder="4字以内..."
        maxlength="4"
        @focus="handleFocus('scene')"
        @blur="handleBlur('scene')"
        @wheel.stop
        @mousedown.stop
      >
    </div>

    <div class="node-section">
      <label class="section-label">图片提示词</label>
      <div class="textarea-autocomplete-wrap">
        <textarea
          ref="imagePromptTextarea"
          v-model="imagePrompt"
          class="textarea textarea-bordered textarea-xs w-full"
          rows="4"
          placeholder="图片生成提示词..."
          @focus="handleFocus('imagePrompt')"
          @blur="handleBlur('imagePrompt')"
          @input="handleAutocompleteInput('imagePrompt', $event)"
          @click="handleCursorChange('imagePrompt')"
          @keyup="handleCursorChange('imagePrompt')"
          @keydown.down.prevent="navigateAutocomplete('imagePrompt', 1)"
          @keydown.up.prevent="navigateAutocomplete('imagePrompt', -1)"
          @keydown.enter.exact.prevent="confirmAutocomplete('imagePrompt')"
          @keydown.esc.prevent="closeAutocomplete('imagePrompt')"
          @wheel.stop
          @mousedown.stop
        ></textarea>
        <div v-if="showImagePromptAutocomplete && filteredImagePromptAssets.length" class="asset-autocomplete prevent-canvas-wheel">
          <button
            v-for="(asset, index) in filteredImagePromptAssets"
            :key="`img-${asset.id}`"
            type="button"
            class="asset-autocomplete-item"
            :class="{ active: highlightedImagePromptIndex === index }"
            @mousedown.prevent="selectAutocomplete('imagePrompt', asset.key)"
          >
            <code>{{ asset.key }}</code>
            <span>{{ asset.group || asset.variable_type_display }}</span>
          </button>
        </div>
      </div>
    </div>

    <div class="node-section">
      <label class="section-label">旁白文案</label>
      <div class="textarea-autocomplete-wrap">
        <textarea
          ref="narrationTextarea"
          v-model="narrationText"
          class="textarea textarea-bordered textarea-xs w-full"
          rows="2"
          placeholder="旁白文案..."
          @focus="handleFocus('narration')"
          @blur="handleBlur('narration')"
          @input="handleAutocompleteInput('narration', $event)"
          @click="handleCursorChange('narration')"
          @keyup="handleCursorChange('narration')"
          @keydown.down.prevent="navigateAutocomplete('narration', 1)"
          @keydown.up.prevent="navigateAutocomplete('narration', -1)"
          @keydown.enter.exact.prevent="confirmAutocomplete('narration')"
          @keydown.esc.prevent="closeAutocomplete('narration')"
          @wheel.stop
          @mousedown.stop
        ></textarea>
        <div v-if="showNarrationAutocomplete && filteredNarrationAssets.length" class="asset-autocomplete prevent-canvas-wheel">
          <button
            v-for="(asset, index) in filteredNarrationAssets"
            :key="`nar-${asset.id}`"
            type="button"
            class="asset-autocomplete-item"
            :class="{ active: highlightedNarrationIndex === index }"
            @mousedown.prevent="selectAutocomplete('narration', asset.key)"
          >
            <code>{{ asset.key }}</code>
            <span>{{ asset.group || asset.variable_type_display }}</span>
          </button>
        </div>
      </div>
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
    },
    assetOptions: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      sceneDescription: this.storyboard.scene_description || '',
      imagePrompt: this.storyboard.image_prompt || '',
      narrationText: this.storyboard.narration_text || '',
      isEditingScene: false,
      isEditingImagePrompt: false,
      isEditingNarration: false,
      showImagePromptAutocomplete: false,
      imagePromptAutocompleteStart: -1,
      imagePromptQuery: '',
      highlightedImagePromptIndex: 0,
      showNarrationAutocomplete: false,
      narrationAutocompleteStart: -1,
      narrationQuery: '',
      highlightedNarrationIndex: 0,
    };
  },
  watch: {
    'storyboard.scene_description': {
      immediate: true,
      handler(newVal) {
        if (!this.isEditingScene) {
          this.sceneDescription = newVal || '';
          this.lastSavedScene = this.sceneDescription;
        }
      }
    },
    'storyboard.image_prompt': {
      immediate: true,
      handler(newVal) {
        if (!this.isEditingImagePrompt) {
          this.imagePrompt = newVal || '';
          this.lastSavedImagePrompt = this.imagePrompt;
        }
      }
    },
    'storyboard.narration_text': {
      immediate: true,
      handler(newVal) {
        if (!this.isEditingNarration) {
          this.narrationText = newVal || '';
          this.lastSavedNarration = this.narrationText;
        }
      }
    }
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
      if (this.storyboard.videos && this.storyboard.videos.length > 0) {
        return 'completed';
      } else if (this.storyboard.images && this.storyboard.images.length > 0) {
        return 'processing';
      }
      return 'pending';
    },
    filteredImagePromptAssets() {
      const keyword = this.imagePromptQuery.trim().toLowerCase();
      if (!keyword) {
        return this.assetOptions;
      }
      return this.assetOptions.filter((asset) => {
        const key = (asset.key || '').toLowerCase();
        const group = (asset.group || '').toLowerCase();
        return key.includes(keyword) || group.includes(keyword);
      });
    },
    filteredNarrationAssets() {
      const keyword = this.narrationQuery.trim().toLowerCase();
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
  methods: {
    handleSave() {
      this.$emit('save', {
        storyboardId: this.storyboard.id,
        data: {
          scene_description: this.sceneDescription,
          image_prompt: this.imagePrompt,
          narration_text: this.narrationText
        },
        silent: false
      });
      this.lastSavedScene = this.sceneDescription;
      this.lastSavedImagePrompt = this.imagePrompt;
      this.lastSavedNarration = this.narrationText;
    },
    handleFocus(field) {
      if (field === 'scene') {
        this.isEditingScene = true;
      } else if (field === 'imagePrompt') {
        this.isEditingImagePrompt = true;
      } else if (field === 'narration') {
        this.isEditingNarration = true;
      }
    },
    handleBlur(field) {
      if (field === 'scene') {
        this.isEditingScene = false;
      } else if (field === 'imagePrompt') {
        this.isEditingImagePrompt = false;
        setTimeout(() => this.closeAutocomplete('imagePrompt'), 120);
      } else if (field === 'narration') {
        this.isEditingNarration = false;
        setTimeout(() => this.closeAutocomplete('narration'), 120);
      }
      this.handleAutoSave();
    },
    handleAutocompleteInput(target, event) {
      this.updateAutocomplete(target, event.target);
    },
    handleCursorChange(target) {
      const refName = target === 'imagePrompt' ? 'imagePromptTextarea' : 'narrationTextarea';
      this.updateAutocomplete(target, this.$refs[refName]);
    },
    updateAutocomplete(target, textarea) {
      if (!textarea) {
        return;
      }
      const value = target === 'imagePrompt' ? this.imagePrompt : this.narrationText;
      const cursor = textarea.selectionStart || 0;
      const textBeforeCursor = value.slice(0, cursor);
      const openIndex = textBeforeCursor.lastIndexOf('{{');
      const closeIndex = textBeforeCursor.lastIndexOf('}}');
      if (openIndex === -1 || closeIndex > openIndex) {
        this.closeAutocomplete(target);
        return;
      }

      const rawQuery = textBeforeCursor.slice(openIndex + 2);
      if (/[^\sa-zA-Z0-9_]/.test(rawQuery)) {
        this.closeAutocomplete(target);
        return;
      }

      if (target === 'imagePrompt') {
        this.imagePromptAutocompleteStart = openIndex;
        this.imagePromptQuery = rawQuery.trimStart();
        this.highlightedImagePromptIndex = 0;
        this.showImagePromptAutocomplete = this.assetOptions.length > 0;
      } else {
        this.narrationAutocompleteStart = openIndex;
        this.narrationQuery = rawQuery.trimStart();
        this.highlightedNarrationIndex = 0;
        this.showNarrationAutocomplete = this.assetOptions.length > 0;
      }
    },
    closeAutocomplete(target) {
      if (target === 'imagePrompt') {
        this.showImagePromptAutocomplete = false;
        this.imagePromptAutocompleteStart = -1;
        this.imagePromptQuery = '';
        this.highlightedImagePromptIndex = 0;
        return;
      }
      this.showNarrationAutocomplete = false;
      this.narrationAutocompleteStart = -1;
      this.narrationQuery = '';
      this.highlightedNarrationIndex = 0;
    },
    navigateAutocomplete(target, step) {
      const list = target === 'imagePrompt' ? this.filteredImagePromptAssets : this.filteredNarrationAssets;
      const visible = target === 'imagePrompt' ? this.showImagePromptAutocomplete : this.showNarrationAutocomplete;
      if (!visible || !list.length) {
        return;
      }
      const total = list.length;
      if (target === 'imagePrompt') {
        this.highlightedImagePromptIndex = (this.highlightedImagePromptIndex + step + total) % total;
      } else {
        this.highlightedNarrationIndex = (this.highlightedNarrationIndex + step + total) % total;
      }
    },
    confirmAutocomplete(target) {
      const list = target === 'imagePrompt' ? this.filteredImagePromptAssets : this.filteredNarrationAssets;
      const index = target === 'imagePrompt' ? this.highlightedImagePromptIndex : this.highlightedNarrationIndex;
      const item = list[index];
      if (item) {
        this.selectAutocomplete(target, item.key);
      }
    },
    selectAutocomplete(target, assetKey) {
      const isImagePrompt = target === 'imagePrompt';
      const textarea = this.$refs[isImagePrompt ? 'imagePromptTextarea' : 'narrationTextarea'];
      const value = isImagePrompt ? this.imagePrompt : this.narrationText;
      const startIndex = isImagePrompt ? this.imagePromptAutocompleteStart : this.narrationAutocompleteStart;
      if (!textarea || startIndex === -1) {
        return;
      }
      const cursor = textarea.selectionStart || 0;
      const token = `{{ ${assetKey} }}`;
      const nextValue = `${value.slice(0, startIndex)}${token}${value.slice(cursor)}`;
      if (isImagePrompt) {
        this.imagePrompt = nextValue;
      } else {
        this.narrationText = nextValue;
      }
      this.closeAutocomplete(target);
      this.$nextTick(() => {
        const nextCursor = startIndex + token.length;
        textarea.focus();
        textarea.setSelectionRange(nextCursor, nextCursor);
      });
      this.handleAutoSave();
    },
    handleAutoSave() {
      const sceneChanged = this.sceneDescription !== this.lastSavedScene;
      const imagePromptChanged = this.imagePrompt !== this.lastSavedImagePrompt;
      const narrationChanged = this.narrationText !== this.lastSavedNarration;
      if (!sceneChanged && !imagePromptChanged && !narrationChanged) {
        return;
      }
      this.$emit('save', {
        storyboardId: this.storyboard.id,
        data: {
          scene_description: this.sceneDescription,
          image_prompt: this.imagePrompt,
          narration_text: this.narrationText
        },
        silent: true
      });
      this.lastSavedScene = this.sceneDescription;
      this.lastSavedImagePrompt = this.imagePrompt;
      this.lastSavedNarration = this.narrationText;
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

.layout-shell.theme-dark .storyboard-node {
  background: #0f172a;
  border-color: hsl(var(--bc) / 0.28);
  box-shadow: 0 4px 16px rgba(2, 6, 23, 0.6);
}

.storyboard-node:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.layout-shell.theme-dark .storyboard-node:hover {
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
  border-color: hsl(var(--wa));
  background: #fffbeb;
}

.layout-shell.theme-dark .status-processing {
  background: rgba(120, 53, 15, 0.2);
}

.status-completed {
  border-color: hsl(var(--su));
  background: #f0fdf4;
}

.layout-shell.theme-dark .status-completed {
  background: rgba(20, 83, 45, 0.2);
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
  gap: 0.5rem;
}

.duration-badge {
  font-size: 0.6875rem;
  padding: 0.25rem 0.5rem;
  background: hsl(var(--bc) / 0.1);
  border-radius: 0.375rem;
  color: hsl(var(--bc) / 0.7);
}

.layout-shell.theme-dark .duration-badge {
  background: hsl(var(--bc) / 0.2);
  color: hsl(var(--bc) / 0.75);
}

.node-section {
  padding: 0.15rem 0.875rem;
  border-bottom: 1px solid hsl(var(--bc) / 0.05);
}

.layout-shell.theme-dark .node-section {
  border-bottom-color: hsl(var(--bc) / 0.15);
}

.node-section-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.875rem;
}

.node-section-compact .section-label {
  margin-bottom: 0;
  white-space: nowrap;
  flex-shrink: 0;
}

.section-label {
  display: block;
  font-size: 0.6875rem;
  font-weight: 600;
  color: hsl(var(--bc) / 0.6);
  margin-bottom: 0.375rem;
}

.textarea-autocomplete-wrap {
  position: relative;
}

.asset-autocomplete {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0.4rem;
  display: grid;
  gap: 0.35rem;
  max-height: 180px;
  overflow-y: auto;
  padding: 0.55rem;
  border-radius: 0.85rem;
  border: 1px solid hsl(var(--bc) / 0.08);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(8px);
  z-index: 20;
}

.layout-shell.theme-dark .asset-autocomplete {
  background: rgba(15, 23, 42, 0.96);
  box-shadow: 0 16px 28px rgba(2, 6, 23, 0.62);
}

.asset-autocomplete-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.45rem 0.6rem;
  border-radius: 0.75rem;
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
</style>
