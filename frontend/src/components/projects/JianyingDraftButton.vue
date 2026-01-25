<template>
  <div class="jianying-draft-button">
    <!-- 生成按钮 -->
    <button
      class="btn btn-primary btn-sm gap-2"
      :class="{ loading: isGenerating }"
      :disabled="isGenerating || !canGenerate"
      @click="handleGenerate"
    >
      <svg
        v-if="!isGenerating"
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
        />
      </svg>
      {{ buttonText }}
    </button>

    <!-- 进度显示模态框 -->
    <dialog ref="progressModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">生成剪映草稿</h3>

        <!-- 进度条 -->
        <div class="mb-4">
          <div class="flex justify-between text-sm mb-2">
            <span>{{ progressMessage }}</span>
            <span>{{ progress }}%</span>
          </div>
          <progress
            class="progress progress-primary w-full"
            :value="progress"
            max="100"
          ></progress>
        </div>

        <!-- 状态信息 -->
        <div v-if="draftPath" class="alert alert-success">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <div class="font-semibold">草稿生成成功！</div>
            <div class="text-sm">路径: {{ draftPath }}</div>
            <div v-if="videoCount" class="text-sm">视频数量: {{ videoCount }}</div>
          </div>
        </div>

        <div v-if="errorMessage" class="alert alert-error">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{{ errorMessage }}</span>
        </div>

        <!-- 操作按钮 -->
        <div class="modal-action">
          <button
            class="btn"
            @click="closeProgressModal"
          >
            关闭
          </button>
        </div>
      </div>
    </dialog>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import wsClient from '@/utils/wsClient';

export default {
  name: 'JianyingDraftButton',
  props: {
    projectId: {
      type: String,
      required: true,
    },
    project: {
      type: Object,
      default: null,
    },
    // 可选参数
    options: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      isGenerating: false,
      progress: 0,
      progressMessage: '准备生成...',
      draftPath: '',
      videoCount: null,
      errorMessage: '',
      ws: null,
    };
  },
  computed: {
    canGenerate() {
      // 检查项目的视频生成阶段是否完成
      if (!this.project) return false;
      // 这里简化处理，实际应该检查 stages
      return this.project.status === 'completed' || this.project.status === 'processing';
    },
    buttonText() {
      if (this.isGenerating) return '生成中...';
      if (this.project?.jianying_draft_path) return '重新生成草稿';
      return '';
    },
  },
  methods: {
    ...mapActions('projects', ['generateJianyingDraft']),

    async handleGenerate() {
      try {
        this.isGenerating = true;
        this.progress = 0;
        this.progressMessage = '准备生成...';
        this.draftPath = '';
        this.videoCount = null;
        this.errorMessage = '';

        // 打开进度模态框
        this.$refs.progressModal.showModal();

        // 调用API
        const result = await this.generateJianyingDraft({
          projectId: this.projectId,
          options: this.options,
        });

        // 成功后显示结果信息
        if (result.draft_path) {
          this.draftPath = result.draft_path;
          this.videoCount = result.video_count;
          this.progress = 100;
          this.progressMessage = '生成完成！';

          // 延迟2秒后自动关闭模态框
          setTimeout(() => {
            this.closeProgressModal();
            this.isGenerating = false;
          }, 2000);
        }

      } catch (error) {
        this.isGenerating = false;
        this.errorMessage = error.response?.data?.error || error.message || '生成失败';
        console.error('生成剪映草稿失败:', error);
      }
    },

  

    closeProgressModal() {
      this.$refs.progressModal.close();
      // 重置状态
      setTimeout(() => {
        this.progress = 0;
        this.progressMessage = '准备生成...';
        this.errorMessage = '';
      }, 300);
    },
  },

  beforeUnmount() {
    // 组件销毁时关闭WebSocket
    if (this.ws) {
      wsClient.close(this.ws);
      this.ws = null;
    }
  },
};
</script>

<style scoped>
.jianying-draft-button {
  display: inline-block;
}
</style>
