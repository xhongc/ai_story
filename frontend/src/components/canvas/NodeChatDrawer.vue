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

        <div class="node-summary card-shell">
          <div class="card-top compact-card-top">
            <div>
              <div class="card-title summary-title">
                当前内容
              </div>
              <div class="card-desc summary-desc">
                AI 会基于这个节点做多轮微调
              </div>
            </div>
          </div>
          <pre class="summary-content">{{ summary }}</pre>
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
            <div class="empty-hero">
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
            :value="value"
            class="composer-input"
            rows="4"
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
        this.$nextTick(() => {
          const list = this.$refs.messageList;
          if (list) {
            list.scrollTop = list.scrollHeight;
          }
        });
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
  gap: 0.9rem;
  padding: 1rem;
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
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

.drawer-title {
  margin: 0.2rem 0 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
}

.layout-shell.theme-dark .drawer-title {
  color: #e2e8f0;
}

.drawer-subtitle {
  margin: 0.2rem 0 0;
  font-size: 0.84rem;
  color: #64748b;
}

.drawer-close {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #0f172a;
  font-size: 1.25rem;
  line-height: 1;
}

.layout-shell.theme-dark .drawer-close {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
}

.card-shell {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.layout-shell.theme-dark .card-shell {
  background: rgba(15, 23, 42, 0.84);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.45);
}

.node-summary,
.composer {
  padding: 0.9rem 1rem;
}

.summary-title {
  font-size: 0.95rem;
}

.summary-desc,
.composer-tip,
.message-status {
  font-size: 0.75rem;
  color: #64748b;
}

.summary-content {
  margin: 0.65rem 0 0;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.78rem;
  line-height: 1.65;
  color: #334155;
}

.layout-shell.theme-dark .summary-content {
  color: #cbd5e1;
}

.quick-actions {
  flex-wrap: wrap;
  gap: 0.55rem;
}

.quick-action-btn,
.apply-action {
  padding: 0.48rem 0.8rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 0.78rem;
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
  gap: 0.85rem;
  padding-right: 0.15rem;
}

.empty-chat {
  padding: 1.25rem 1rem;
  border-radius: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.5);
  text-align: center;
}

.layout-shell.theme-dark .empty-chat {
  background: rgba(15, 23, 42, 0.6);
}

.message-card {
  max-width: 92%;
  padding: 0.85rem 1rem;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
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
  font-size: 0.76rem;
  font-weight: 700;
  color: #0f766e;
}

.message-status.success {
  color: #16a34a;
}

.message-content {
  margin-top: 0.5rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.9rem;
  line-height: 1.7;
  color: #1e293b;
}

.layout-shell.theme-dark .message-content {
  color: #e2e8f0;
}

.message-footer {
  margin-top: 0.7rem;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.composer-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.9rem 1rem;
  font-size: 0.9rem;
  line-height: 1.7;
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
  gap: 0.65rem;
}

.primary-action,
.secondary-action {
  padding: 0.58rem 1rem;
  border-radius: 999px;
  font-size: 0.82rem;
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
    padding: 0.85rem;
  }

  .message-card {
    max-width: 100%;
  }
}
</style>
