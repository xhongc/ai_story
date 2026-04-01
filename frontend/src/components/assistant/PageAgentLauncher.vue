<template>
  <div class="page-agent-shell">
    <PageAgentDialog
      :visible="visible"
      :context-title="currentContext?.title || '当前页面'"
      :context-subtitle="currentContext?.subtitle || '页面助手'"
      :summary="currentContext?.summary || ''"
      :quick-actions="currentContext?.quickActions || []"
      :messages="messages"
      :value="draft"
      :streaming="streaming"
      @close="close"
      @input="updateDraft"
      @submit="sendCurrentDraft"
      @stop="abort"
      @quick-action="sendMessage"
      @execute-suggestion="executeSuggestion"
    />

    <button
      v-if="!visible"
      class="agent-launcher"
      type="button"
      :aria-expanded="String(visible)"
      :title="visible ? '关闭页面助手' : '打开页面助手'"
      @click="toggle"
    >
      <span class="launcher-core">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M12 2.75L13.817 8.183L19.25 10L13.817 11.817L12 17.25L10.183 11.817L4.75 10L10.183 8.183L12 2.75Z"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M18.5 15.5L19.232 17.518L21.25 18.25L19.232 18.982L18.5 21L17.768 18.982L15.75 18.25L17.768 17.518L18.5 15.5Z"
            fill="currentColor"
          />
        </svg>
      </span>
    </button>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import PageAgentDialog from './PageAgentDialog.vue';
import { buildFallbackPageAgentContext } from '@/services/pageAgent/contextBuilders';

export default {
  name: 'PageAgentLauncher',
  components: {
    PageAgentDialog,
  },
  computed: {
    ...mapGetters('assistant', ['visible', 'streaming', 'draft', 'currentContext', 'messages']),
  },
  watch: {
    '$route.fullPath': {
      immediate: true,
      handler() {
        this.ensureFallbackContext();
      },
    },
  },
  methods: {
    ...mapActions('assistant', ['toggle', 'close', 'updateDraft', 'sendMessage', 'executeSuggestion', 'registerContext', 'abort']),
    ensureFallbackContext() {
      if (
        this.currentContext
        && this.currentContext.pageType !== 'generic'
        && this.currentContext.meta?.routeName === this.$route.name
      ) {
        return;
      }
      this.registerContext(buildFallbackPageAgentContext(this.$route));
    },
    sendCurrentDraft() {
      this.sendMessage(this.draft);
    },
  },
};
</script>

<style scoped>
.page-agent-shell {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 425;
}

.agent-launcher {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  padding: 0;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.14);
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .agent-launcher {
  background: rgba(15, 23, 42, 0.94);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.22);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.5);
}

.agent-launcher:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 18px 36px rgba(20, 184, 166, 0.22);
  transform: translateY(-2px);
}

.launcher-core {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.16), rgba(14, 165, 233, 0.16));
  color: #0f766e;
}

.layout-shell.theme-dark .launcher-core {
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.2), rgba(14, 165, 233, 0.2));
  color: #5eead4;
}

.launcher-core svg {
  width: 22px;
  height: 22px;
}

@media (max-width: 768px) {
  .page-agent-shell {
    right: 12px;
    bottom: 16px;
  }

  .agent-launcher {
    width: 58px;
    height: 58px;
  }

  .launcher-core {
    width: 44px;
    height: 44px;
  }
}
</style>
