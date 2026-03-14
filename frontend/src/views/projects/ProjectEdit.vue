<template>
  <div class="page-shell project-edit-page">
    <div class="page-header">
      <div class="page-header-main">
        <button class="back-link" @click="goBack">← 返回</button>
        <h1 class="page-title">编辑分集</h1>
        <p class="page-subtitle">调整分集信息与原始主题，作品工作流配置会继续沿用。</p>
      </div>
    </div>

    <LoadingContainer :loading="loading">
      <div class="form-panel">
        <form class="form-body" @submit.prevent="handleSubmit">
          <div class="form-grid two-columns">
            <div class="form-control">
              <label class="field-label">所属作品 <span class="required-mark">*</span></label>
              <select v-model="form.series" class="field-input" :disabled="loadingSeries">
                <option :value="null" disabled>{{ loadingSeries ? '加载中...' : '请选择作品' }}</option>
                <option v-for="item in seriesList" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </div>
            <div class="form-control">
              <label class="field-label">提示词集</label>
              <select v-model="form.prompt_template_set" class="field-input" :disabled="loadingTemplates">
                <option :value="null" disabled>{{ loadingTemplates ? '加载中...' : '请选择提示词集' }}</option>
                <option v-for="set in templateSets" :key="set.id" :value="set.id">{{ set.name }}</option>
              </select>
            </div>
          </div>

          <div class="form-grid two-columns">
            <div class="form-control">
              <label class="field-label">分集序号 <span class="required-mark">*</span></label>
              <input v-model.number="form.episode_number" type="number" min="1" class="field-input" placeholder="1">
            </div>
            <div class="form-control">
              <label class="field-label">分集标题 <span class="required-mark">*</span></label>
              <input v-model="form.episode_title" type="text" class="field-input" placeholder="例如：石猴出世">
            </div>
          </div>

          <div class="form-grid two-columns">
            <div class="form-control">
              <label class="field-label">分集名称</label>
              <input v-model="form.name" type="text" class="field-input" placeholder="例如：第一集">
            </div>
            <div class="form-control">
              <label class="field-label">分集描述</label>
              <input v-model="form.description" type="text" class="field-input" placeholder="一句话描述这一集的主题">
            </div>
          </div>

          <div class="form-control">
            <label class="field-label">原始主题或文案 <span class="required-mark">*</span></label>
            <textarea
              v-model="form.original_topic"
              class="field-input field-textarea"
              :class="{ 'field-error': errors.original_topic }"
              placeholder="请输入这一集的原始主题、剧情简介或完整文案..."
            ></textarea>
            <p v-if="errors.original_topic" class="error-text">{{ errors.original_topic }}</p>
          </div>

          <div class="submit-bar">
            <button type="button" class="ghost-link" @click="goBack" :disabled="submitting">取消</button>
            <button type="submit" class="primary-action" :disabled="submitting">
              <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
              <span>{{ submitting ? '保存中...' : '保存分集' }}</span>
            </button>
          </div>
        </form>
      </div>
    </LoadingContainer>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { promptSetAPI } from '@/api/prompts';
import LoadingContainer from '@/components/common/LoadingContainer.vue';

export default {
  name: 'ProjectEdit',
  components: {
    LoadingContainer,
  },
  data() {
    return {
      loading: false,
      loadingSeries: false,
      loadingTemplates: false,
      submitting: false,
      submitTried: false,
      templateSets: [],
      form: {
        series: null,
        episode_number: 1,
        episode_title: '',
        name: '',
        description: '',
        original_topic: '',
        prompt_template_set: null,
      },
      errors: {
        original_topic: '',
      },
    };
  },
  computed: {
    ...mapState('projects', ['seriesList']),
  },
  async created() {
    await Promise.all([this.fetchProjectData(), this.fetchSeriesOptions(), this.fetchTemplateSets()]);
  },
  methods: {
    ...mapActions('projects', ['fetchProject', 'updateProject', 'fetchSeries']),
    async fetchProjectData() {
      this.loading = true;
      try {
        const project = await this.fetchProject(this.$route.params.id);
        this.form = {
          series: project.series || null,
          episode_number: project.episode_number || 1,
          episode_title: project.episode_title || '',
          name: project.name || '',
          description: project.description || '',
          original_topic: project.original_topic || '',
          prompt_template_set: project.prompt_template_set || null,
        };
      } catch (error) {
        console.error('Failed to fetch project:', error);
        this.$message.error('加载分集失败');
      } finally {
        this.loading = false;
      }
    },
    async fetchSeriesOptions() {
      this.loadingSeries = true;
      try {
        await this.fetchSeries();
      } finally {
        this.loadingSeries = false;
      }
    },
    async fetchTemplateSets() {
      this.loadingTemplates = true;
      try {
        const response = await promptSetAPI.getList({ is_active: true, page_size: 100 });
        this.templateSets = response.results || response || [];
      } finally {
        this.loadingTemplates = false;
      }
    },
    validateForm() {
      this.submitTried = true;
      this.errors = { original_topic: '' };

      if (!this.form.series) {
        this.$message.error('请选择所属作品');
        return false;
      }
      if (!this.form.episode_number || this.form.episode_number < 1) {
        this.$message.error('请输入有效的分集序号');
        return false;
      }
      if (!this.form.episode_title.trim()) {
        this.$message.error('请输入分集标题');
        return false;
      }
      if (!this.form.original_topic.trim()) {
        this.errors.original_topic = '请输入原始主题或文案';
        return false;
      }
      return true;
    },
    async handleSubmit() {
      if (!this.validateForm()) {
        return;
      }

      this.submitting = true;
      try {
        const project = await this.updateProject({
          id: this.$route.params.id,
          data: {
            series: this.form.series,
            episode_number: this.form.episode_number,
            episode_title: this.form.episode_title.trim(),
            name: this.form.name.trim(),
            description: this.form.description.trim(),
            original_topic: this.form.original_topic.trim(),
            prompt_template_set: this.form.prompt_template_set,
          },
        });
        this.$message.success('分集已保存');
        this.$router.push({ name: 'ProjectDetail', params: { id: project.id } });
      } catch (error) {
        console.error('Failed to update project:', error);
        this.$message.error('保存分集失败');
      } finally {
        this.submitting = false;
      }
    },
    goBack() {
      this.$router.back();
    },
  },
};
</script>

<style scoped>
.page-shell {
  min-height: 100%;
  padding: 2.5rem 3.5rem 3rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.page-header-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.back-link {
  border: none;
  background: transparent;
  padding: 0;
  color: #64748b;
  cursor: pointer;
  text-align: left;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.layout-shell.theme-dark .page-title {
  color: #e2e8f0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.form-panel {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%)
      0 0 / 100% 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .form-panel {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%)
      0 0 / 100% 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.75rem;
}

.form-grid {
  display: grid;
  gap: 1rem;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.form-control {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.field-label {
  font-size: 0.92rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .field-label {
  color: #e2e8f0;
}

.required-mark {
  color: #ef4444;
}

.field-input {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.92);
  padding: 0.85rem 1rem;
  color: #0f172a;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .field-input {
  background: rgba(15, 23, 42, 0.88);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.2);
}

.field-input:focus {
  outline: none;
  border-color: rgba(20, 184, 166, 0.55);
  box-shadow: 0 0 0 4px rgba(45, 212, 191, 0.14);
}

.field-textarea {
  min-height: 220px;
  resize: vertical;
}

.field-error {
  border-color: rgba(239, 68, 68, 0.58);
}

.error-text {
  margin: 0;
  font-size: 0.85rem;
  color: #dc2626;
}

.submit-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.85rem;
  padding-top: 0.5rem;
}

.ghost-link,
.primary-action {
  border-radius: 999px;
  padding: 0.78rem 1.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ghost-link {
  background: transparent;
  border: 1px solid rgba(148, 163, 184, 0.24);
  color: #475569;
}

.primary-action {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
}

.layout-shell.theme-dark .ghost-link {
  color: #cbd5e1;
  border-color: rgba(148, 163, 184, 0.2);
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.24);
}

.primary-action:hover,
.ghost-link:hover {
  transform: translateY(-1px);
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.55);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
}

@media (max-width: 960px) {
  .page-shell {
    padding: 1.5rem;
  }

  .two-columns {
    grid-template-columns: 1fr;
  }

  .submit-bar {
    justify-content: stretch;
    flex-direction: column-reverse;
  }

  .ghost-link,
  .primary-action {
    width: 100%;
    justify-content: center;
  }
}
</style>
