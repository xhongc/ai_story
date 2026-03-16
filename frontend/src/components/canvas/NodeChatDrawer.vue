<template>
  <transition name="node-chat-drawer">
    <aside
      v-if="visible"
      class="node-chat-drawer"
      @click.stop
    >
      <div class="drawer-panel">
        <div class="drawer-header">
          <div>
            <div class="drawer-eyebrow">
              节点对话编辑
            </div>
            <h3 class="drawer-title">
              {{ title }}
            </h3>
            <p class="drawer-subtitle">
              {{ subtitle }}
            </p>
          </div>
          <button
            class="drawer-close"
            type="button"
            @click="$emit('close')"
          >
            ×
          </button>
        </div>

        <div
          class="node-summary card-shell"
          :class="{ collapsed: !summaryExpanded }"
        >
          <button
            class="summary-toggle compact-card-top"
            type="button"
            @click="summaryExpanded = !summaryExpanded"
          >
            <div>
              <div class="card-title summary-title">
                当前内容
              </div>
              <div class="card-desc summary-desc">
                默认收起，按需展开查看完整上下文
              </div>
            </div>
            <span
              class="summary-toggle-text"
            >
              {{ summaryExpanded ? '收起' : '展开' }}
            </span>
          </button>
          <pre
            v-show="summaryExpanded"
            class="summary-content"
          >{{ summary }}</pre>
        </div>

        <div class="quick-actions">
          <button
            v-for="item in quickActions"
            :key="item"
            class="quick-action-btn"
            type="button"
            @click="$emit('quick-action', item)"
          >
            {{ item }}
          </button>
        </div>

        <div
          ref="messageList"
          class="message-list"
        >
          <div
            v-if="messages.length === 0"
            class="empty-chat"
          >
            <div
              class="empty-hero"
            >
              开始一次节点对话
            </div>
            <p class="empty-hint">
              描述你希望修改的风格、节奏、细节或镜头意图
            </p>
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            :class="['message-card', `role-${message.role}`]"
          >
            <div class="message-meta">
              <span class="message-role">
                {{ message.role === 'user' ? '你' : 'AI 助手' }}
              </span>
              <span
                v-if="message.streaming"
                class="message-status"
              >
                流式生成中
              </span>
              <span
                v-else-if="message.applied"
                class="message-status success"
              >
                已应用
              </span>
            </div>
            <div class="message-content">
              {{ message.content || (message.streaming ? '正在生成中...' : '') }}
            </div>
            <div
              v-if="message.role === 'assistant' && message.applyPatch"
              class="patch-preview"
            >
              <button
                class="patch-toggle"
                type="button"
                @click="togglePatchExpanded(message.id)"
              >
                <span>applyPatch</span>
                <span>{{ isPatchExpanded(message.id) ? '收起' : '展开' }}</span>
              </button>
              <pre
                v-show="isPatchExpanded(message.id)"
                class="patch-content"
              >{{ formatPatch(message.applyPatch) }}</pre>
            </div>
            <div
              v-if="message.role === 'assistant' && message.applyPatch"
              class="message-footer"
            >
              <button
                class="apply-action"
                type="button"
                :disabled="message.streaming || applying"
                @click="$emit('apply', message)"
              >
                {{ applying ? '应用中...' : '快捷应用' }}
              </button>
            </div>
          </article>
        </div>

        <div class="composer card-shell">
          <textarea
            ref="composerInput"
            :value="value"
            class="composer-input"
            rows="3"
            placeholder="例如：保留原意，但让画面更电影感，旁白更精炼。"
            @input="$emit('input', $event.target.value)"
            @keydown.meta.enter.prevent="$emit('submit')"
            @keydown.ctrl.enter.prevent="$emit('submit')"
          />
          <div class="composer-footer">
            <span class="composer-tip">
              ⌘/Ctrl + Enter 发送
            </span>
            <div class="composer-actions">
              <button
                v-if="streaming"
                class="secondary-action"
                type="button"
                @click="$emit('stop')"
              >
                停止生成
              </button>
              <button
                class="primary-action"
                type="button"
                :disabled="streaming || !value.trim()"
                @click="$emit('submit')"
              >
                {{ streaming ? '生成中...' : '发送' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </transition>
</template>

<script>
export default {
  name: 'NodeChatDrawer',
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    subtitle: {
      type: String,
      default: '',
    },
    summary: {
      type: String,
      default: '',
    },
    value: {
      type: String,
      default: '',
    },
    messages: {
      type: Array,
      default: () => [],
    },
    quickActions: {
      type: Array,
      default: () => [],
    },
    streaming: {
      type: Boolean,
      default: false,
    },
    applying: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      summaryExpanded: false,
      expandedPatches: {},
    };
  },
  watch: {
    messages: {
      deep: true,
      handler() {
        this.$nextTick(() => {
          const list = this.$refs.messageList;
          if (list) {
            list.scrollTop = list.scrollHeight;
          }
        });
      },
    },
    visible(isVisible) {
      if (isVisible) {
        this.summaryExpanded = false;
        this.expandedPatches = {};
        this.$nextTick(() => {
          const list = this.$refs.messageList;
          if (list) {
            list.scrollTop = list.scrollHeight;
          }
        });
      }
    },
  },
  methods: {
    focusInputToEnd() {
      this.$nextTick(() => {
        const textarea = this.$refs.composerInput;
        if (!textarea) {
          return;
        }
        textarea.focus();
        const length = textarea.value ? textarea.value.length : 0;
        textarea.setSelectionRange(length, length);
      });
    },
    isPatchExpanded(messageId) {
      return Boolean(this.expandedPatches[messageId]);
    },
    togglePatchExpanded(messageId) {
      this.$set(this.expandedPatches, messageId, !this.isPatchExpanded(messageId));
    },
    formatPatch(patch) {
      try {
        return JSON.stringify(patch, null, 2);
      } catch (error) {
        return String(patch || '');
      }
    },
  },
};
</script>

<style scoped>
.node-chat-drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: min(560px, calc(100vw - 24px));
  height: 100vh;
  z-index: 420;
  pointer-events: auto;
}

.drawer-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 0.8rem;
  border-left: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.95);
  backdrop-filter: blur(16px);
  box-shadow: -20px 0 48px rgba(15, 23, 42, 0.18);
}

.layout-shell.theme-dark .drawer-panel {
  background: rgba(2, 6, 23, 0.92);
  border-left-color: rgba(148, 163, 184, 0.2);
  box-shadow: -20px 0 48px rgba(2, 6, 23, 0.6);
}

.drawer-header,
.composer-footer,
.message-meta,
.message-footer,
.compact-card-top,
.quick-actions {
  display: flex;
  align-items: center;
}

.drawer-header,
.composer-footer,
.message-meta,
.message-footer,
.compact-card-top {
  justify-content: space-between;
}

.drawer-eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

.drawer-title {
  margin: 0.15rem 0 0;
  font-size: 1.06rem;
  font-weight: 700;
  color: #0f172a;
}

.layout-shell.theme-dark .drawer-title {
  color: #e2e8f0;
}

.drawer-subtitle {
  margin: 0.12rem 0 0;
  font-size: 0.8rem;
  color: #64748b;
}

.drawer-close {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #0f172a;
  font-size: 1.2rem;
  line-height: 1;
}

.layout-shell.theme-dark .drawer-close {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
}

.card-shell {
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

.layout-shell.theme-dark .card-shell {
  background: rgba(15, 23, 42, 0.84);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 14px 30px rgba(2, 6, 23, 0.45);
}

.node-summary,
.composer {
  padding: 0.6rem 0.75rem;
}

.node-summary.collapsed {
  padding-bottom: 0.45rem;
}

.summary-toggle {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.summary-title {
  font-size: 0.88rem;
}

.summary-desc,
.composer-tip,
.message-status,
.summary-toggle-text {
  font-size: 0.72rem;
  color: #64748b;
}

.summary-toggle-text {
  font-weight: 600;
}

.summary-content {
  margin: 0.45rem 0 0;
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.74rem;
  line-height: 1.55;
  color: #334155;
}

.layout-shell.theme-dark .summary-content {
  color: #cbd5e1;
}

.quick-actions {
  flex-wrap: wrap;
  gap: 0.45rem;
}

.quick-action-btn,
.apply-action {
  padding: 0.4rem 0.7rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 0.76rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.quick-action-btn:hover,
.apply-action:hover,
.drawer-close:hover {
  border-color: rgba(20, 184, 166, 0.45);
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.14);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .quick-action-btn,
.layout-shell.theme-dark .apply-action {
  background: rgba(15, 23, 42, 0.96);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.2);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  padding-right: 0.1rem;
}

.empty-chat {
  padding: 0.9rem 0.75rem;
  border-radius: 16px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.5);
  text-align: center;
}

.layout-shell.theme-dark .empty-chat {
  background: rgba(15, 23, 42, 0.6);
}

.message-card {
  max-width: 92%;
  padding: 0.55rem 0.7rem;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.message-card.role-user {
  align-self: flex-end;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.16), rgba(14, 165, 233, 0.14));
}

.message-card.role-assistant {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.85);
}

.layout-shell.theme-dark .message-card.role-user {
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.2), rgba(14, 165, 233, 0.18));
}

.layout-shell.theme-dark .message-card.role-assistant {
  background: rgba(15, 23, 42, 0.86);
}

.message-role {
  font-size: 0.74rem;
  font-weight: 700;
  color: #0f766e;
}

.message-status.success {
  color: #16a34a;
}

.message-content {
  margin-top: 0.28rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.84rem;
  line-height: 1.55;
  color: #1e293b;
}

.layout-shell.theme-dark .message-content {
  color: #e2e8f0;
}

.patch-preview {
  margin-top: 0.45rem;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.82);
  overflow: hidden;
}

.layout-shell.theme-dark .patch-preview {
  background: rgba(15, 23, 42, 0.78);
  border-color: rgba(148, 163, 184, 0.18);
}

.patch-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.42rem 0.58rem;
  border: 0;
  background: transparent;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.layout-shell.theme-dark .patch-toggle {
  color: #cbd5e1;
}

.patch-content {
  margin: 0;
  padding: 0 0.58rem 0.58rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.72rem;
  line-height: 1.5;
  color: #334155;
}

.layout-shell.theme-dark .patch-content {
  color: #cbd5e1;
}

.message-footer {
  margin-top: 0.45rem;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.composer-input {
  width: 100%;
  min-height: 88px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.65rem 0.8rem;
  font-size: 0.84rem;
  line-height: 1.55;
  color: #0f172a;
  resize: vertical;
}

.layout-shell.theme-dark .composer-input {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.22);
}

.composer-input:focus {
  outline: none;
  border-color: rgba(20, 184, 166, 0.5);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.12);
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.primary-action,
.secondary-action {
  padding: 0.48rem 0.9rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.primary-action {
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #ffffff;
  color: #0f172a;
}

.primary-action:hover:not(:disabled),
.secondary-action:hover:not(:disabled) {
  border-color: rgba(20, 184, 166, 0.55);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.secondary-action {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: transparent;
  color: #334155;
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.96);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.24);
}

.layout-shell.theme-dark .secondary-action {
  color: #cbd5e1;
}

.primary-action:disabled,
.secondary-action:disabled,
.apply-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.node-chat-drawer-enter-active,
.node-chat-drawer-leave-active {
  transition: all 0.22s ease;
}

.node-chat-drawer-enter,
.node-chat-drawer-leave-to {
  opacity: 0;
  transform: translateX(24px);
}

@media (max-width: 768px) {
  .node-chat-drawer {
    width: 100vw;
  }

  .drawer-panel {
    padding: 0.7rem;
  }

  .message-card {
    max-width: 100%;
  }
}
</style>
