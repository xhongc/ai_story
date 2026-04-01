<template>
  <transition name="page-agent-dialog">
    <section
      v-if="visible"
      class="page-agent-dialog"
      @click.stop
    >
      <div class="dialog-panel">
        <div class="dialog-header">
          <div class="dialog-header-main">
            <div class="dialog-eyebrow">
              页面助手
            </div>
            <h3 class="dialog-title">
              {{ contextTitle }}
            </h3>
            <p class="dialog-subtitle">
              {{ contextSubtitle }}
            </p>
          </div>
          <button
            class="dialog-close"
            type="button"
            @click="$emit('close')"
          >
            ×
          </button>
        </div>

        <div
          v-if="quickActions.length"
          class="quick-actions"
        >
          <button
            v-for="item in quickActions"
            :key="item"
            class="quick-action-btn"
            type="button"
            :disabled="streaming"
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
              助手已准备就绪
            </div>
            <p class="empty-hint">
              你可以让我总结当前页面、给下一步建议，或执行已开放的页面内操作。
            </p>
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            :class="['message-card', `role-${message.role}`]"
          >
            <div class="message-meta">
              <span class="message-role">
                {{ message.role === 'user' ? '你' : '页面助手' }}
              </span>
              <span
                v-if="message.pending"
                class="message-status"
              >
                处理中
              </span>
            </div>
            <div class="message-content">
              {{ message.content }}
            </div>

            <div
              v-if="message.suggestions && message.suggestions.length"
              class="suggestion-list"
            >
              <button
                v-for="suggestion in message.suggestions"
                :key="suggestion.id"
                class="suggestion-btn"
                type="button"
                :disabled="streaming"
                @click="$emit('execute-suggestion', suggestion)"
              >
                <span>{{ suggestion.label }}</span>
                <small v-if="suggestion.description">{{ suggestion.description }}</small>
              </button>
            </div>
          </article>
        </div>

        <div class="composer-card">
          <textarea
            ref="composerInput"
            :value="value"
            class="composer-input"
            rows="3"
            placeholder="例如：总结当前项目进度，或者帮我定位到分镜阶段。"
            @input="$emit('input', $event.target.value)"
            @keydown.meta.enter.prevent="$emit('submit')"
            @keydown.ctrl.enter.prevent="$emit('submit')"
          />
          <div class="composer-footer">
            <span class="composer-tip">⌘/Ctrl + Enter 发送</span>
            <div class="composer-actions">
              <button
                v-if="streaming"
                class="secondary-action"
                type="button"
                @click="$emit('stop')"
              >
                停止
              </button>
              <button
                class="primary-action"
                type="button"
                :disabled="streaming || !value.trim()"
                @click="$emit('submit')"
              >
                {{ streaming ? '处理中...' : '发送' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </transition>
</template>

<script>
export default {
  name: 'PageAgentDialog',
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    contextTitle: {
      type: String,
      default: '当前页面',
    },
    contextSubtitle: {
      type: String,
      default: '页面助手',
    },
    summary: {
      type: String,
      default: '',
    },
    quickActions: {
      type: Array,
      default: () => [],
    },
    messages: {
      type: Array,
      default: () => [],
    },
    value: {
      type: String,
      default: '',
    },
    streaming: {
      type: Boolean,
      default: false,
    },
  },
  watch: {
    messages: {
      deep: true,
      handler() {
        this.scrollToBottom();
      },
    },
    visible(nextVisible) {
      if (nextVisible) {
        this.$nextTick(() => {
          this.scrollToBottom();
          this.$refs.composerInput?.focus();
        });
      }
    },
  },
  methods: {
    scrollToBottom() {
      this.$nextTick(() => {
        const list = this.$refs.messageList;
        if (list) {
          list.scrollTop = list.scrollHeight;
        }
      });
    },
  },
};
</script>

<style scoped>
.page-agent-dialog {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: min(440px, calc(100vw - 32px));
  height: min(760px, calc(100vh - 48px));
  z-index: 430;
}

.dialog-panel {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.9rem;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
  box-shadow: 0 28px 56px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}

.dialog-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.95), rgba(14, 165, 233, 0.85));
}

.layout-shell.theme-dark .dialog-panel {
  background: rgba(15, 23, 42, 0.94);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 28px 56px rgba(2, 6, 23, 0.62);
}

.dialog-header,
.composer-footer,
.message-meta,
.composer-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dialog-header,
.composer-footer,
.message-meta {
  justify-content: space-between;
}

.dialog-header-main {
  min-width: 0;
}

.dialog-eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f766e;
}

.dialog-title {
  margin: 0.18rem 0 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.dialog-subtitle,
.summary-title,
.composer-tip,
.message-status,
.suggestion-btn small {
  font-size: 0.74rem;
  color: #64748b;
}

.dialog-subtitle,
.summary-text {
  margin: 0.18rem 0 0;
}

.layout-shell.theme-dark .dialog-title {
  color: #e2e8f0;
}

.dialog-close,
.quick-action-btn,
.suggestion-btn,
.primary-action,
.secondary-action {
  transition: all 0.2s ease;
}

.dialog-close {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font-size: 1.2rem;
  line-height: 1;
}

.summary-card,
.composer-card {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

.layout-shell.theme-dark .summary-card,
.layout-shell.theme-dark .composer-card {
  background: rgba(15, 23, 42, 0.84);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 14px 30px rgba(2, 6, 23, 0.45);
}

.summary-card {
  padding: 0.75rem 0.85rem;
}

.summary-title {
  font-weight: 700;
}

.summary-text {
  font-size: 0.84rem;
  line-height: 1.6;
  color: #334155;
}

.layout-shell.theme-dark .summary-text,
.layout-shell.theme-dark .message-content {
  color: #e2e8f0;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.quick-action-btn,
.primary-action,
.secondary-action {
  padding: 0.6rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 0.8rem;
  font-weight: 600;
}

.quick-action-btn:hover,
.dialog-close:hover,
.suggestion-btn:hover,
.primary-action:hover,
.secondary-action:hover {
  border-color: rgba(20, 184, 166, 0.5);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.16);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .dialog-close,
.layout-shell.theme-dark .quick-action-btn,
.layout-shell.theme-dark .primary-action,
.layout-shell.theme-dark .secondary-action,
.layout-shell.theme-dark .suggestion-btn {
  background: rgba(15, 23, 42, 0.96);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.2);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding-right: 0.1rem;
}

.empty-chat {
  padding: 1rem 0.85rem;
  border-radius: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.48);
  text-align: center;
}

.layout-shell.theme-dark .empty-chat {
  background: rgba(15, 23, 42, 0.58);
}

.empty-hero {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.empty-hint {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  line-height: 1.6;
  color: #64748b;
}

.layout-shell.theme-dark .empty-hero {
  color: #f8fafc;
}

.message-card {
  max-width: 92%;
  padding: 0.68rem 0.8rem;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.message-card.role-user {
  align-self: flex-end;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.16), rgba(14, 165, 233, 0.14));
}

.message-card.role-assistant {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.84);
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

.message-content {
  margin-top: 0.32rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.86rem;
  line-height: 1.58;
  color: #1e293b;
}

.suggestion-list {
  margin-top: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.suggestion-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.12rem;
  width: 100%;
  padding: 0.62rem 0.72rem;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(248, 250, 252, 0.92);
  color: #0f172a;
  text-align: left;
}

.composer-card {
  padding: 0.7rem 0.75rem;
}

.composer-input {
  width: 100%;
  resize: none;
  border: 0;
  background: transparent;
  color: #0f172a;
  font-size: 0.9rem;
  line-height: 1.6;
  outline: none;
}

.composer-input::placeholder {
  color: #94a3b8;
}

.layout-shell.theme-dark .composer-input {
  color: #e2e8f0;
}

.page-agent-dialog-enter-active,
.page-agent-dialog-leave-active {
  transition: all 0.22s ease;
}

.page-agent-dialog-enter,
.page-agent-dialog-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}

@media (max-width: 768px) {
  .page-agent-dialog {
    right: 12px;
    left: 12px;
    bottom: 12px;
    width: auto;
    height: min(82vh, 760px);
  }
}
</style>
