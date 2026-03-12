<template>
  <div class="page-shell project-create-page">
    <div class="page-header">
      <div class="page-header-main">
        <button class="back-link" @click="goBack">← 返回</button>
        <h1 class="page-title">创建分集</h1>
        <p class="page-subtitle">
          支持单集创建和批量创建，批量模式会复用同一套基础配置。
        </p>
      </div>
    </div>

    <div class="form-layout">
      <form class="form-body" @submit.prevent="handleSubmit">
        <div class="mode-section">
          <div class="mode-switch">
            <button
              type="button"
              :class="['mode-option', { active: form.mode === 'single' }]"
              @click="switchMode('single')"
            >
              单集创建
            </button>
            <button
              type="button"
              :class="['mode-option', { active: form.mode === 'batch' }]"
              @click="switchMode('batch')"
            >
              批量创建
            </button>
          </div>
        </div>

        <div class="card-block">
          <div class="card-top">
            <div>
              <h2 class="card-title">基础配置</h2>
              <p class="card-desc">这些配置会应用到本次创建的全部分集。</p>
            </div>
          </div>

          <div class="card-meta form-grid two-columns">
            <div class="form-control">
              <label class="field-label">所属作品 <span class="required-mark">*</span></label>
              <select v-model="form.series" class="field-input" :class="{ 'field-error': !form.series && submitTried }">
                <option :value="null" disabled>请选择作品</option>
                <option v-for="item in seriesList" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </div>
            <div class="form-control">
              <label class="field-label">提示词集</label>
              <select v-model="form.prompt_template_set" class="field-input" :disabled="loadingTemplates">
                <option :value="null">{{ loadingTemplates ? '加载中...' : '使用默认提示词集' }}</option>
                <option v-for="set in templateSets" :key="set.id" :value="set.id">{{ set.name }}</option>
              </select>
            </div>
          </div>

          <div class="card-footer form-grid two-columns">
            <div class="form-control">
              <label class="field-label">分集描述</label>
              <input
                v-model="form.description"
                type="text"
                class="field-input"
                placeholder="一句话描述这一批分集的共同主题"
              >
            </div>
            <div v-if="form.mode === 'batch'" class="form-control">
              <label class="field-label">起始分集序号 <span class="required-mark">*</span></label>
              <input
                v-model.number="form.start_episode_number"
                type="number"
                min="1"
                class="field-input"
                :class="{ 'field-error': errors.start_episode_number }"
                placeholder="例如：12"
              >
              <p v-if="errors.start_episode_number" class="error-text">{{ errors.start_episode_number }}</p>
            </div>
          </div>
        </div>

        <div v-if="form.mode === 'single'" class="card-block">
          <div class="card-top">
            <div>
              <h2 class="card-title">分集信息</h2>
              <p class="card-desc">填写这一集的标题、名称和原始文案。</p>
            </div>
          </div>

          <div class="card-meta form-grid two-columns">
            <div class="form-control">
              <label class="field-label">分集序号 <span class="required-mark">*</span></label>
              <input v-model.number="form.episode_number" type="number" min="1" class="field-input" placeholder="1">
            </div>
            <div class="form-control">
              <label class="field-label">分集标题 <span class="required-mark">*</span></label>
              <input v-model="form.episode_title" type="text" class="field-input" placeholder="例如：石猴出世" @input="handleSingleTitleInput">
            </div>
          </div>

          <div class="card-meta form-grid two-columns">
            <div class="form-control">
              <label class="field-label">分集名称</label>
              <input v-model="form.name" type="text" class="field-input" placeholder="例如：第1集">
            </div>
            <div class="form-control form-control--hint">
              <span class="field-label">自动命名</span>
              <p class="helper-text">若名称留空，将按“第N集”自动生成。</p>
            </div>
          </div>

          <div class="card-footer form-control">
            <label class="field-label">原始主题或文案 <span class="required-mark">*</span></label>
            <textarea
              v-model="form.original_topic"
              class="field-input field-textarea"
              @input="handleSingleTopicInput"
              :class="{ 'field-error': errors.original_topic }"
              placeholder="请输入这一集的原始主题、剧情简介或完整文案..."
            ></textarea>
            <p v-if="errors.original_topic" class="error-text">{{ errors.original_topic }}</p>
          </div>
        </div>

        <div v-else class="card-block">
          <div class="card-top">
            <div>
              <h2 class="card-title">批量分集列表</h2>
              <p class="card-desc">每行一集，序号会从起始分集序号开始自动递增。</p>
            </div>
            <button type="button" class="secondary-action" @click="addBatchEpisode">新增一集</button>
          </div>

          <div v-if="submitTried && errors.batch_episodes" class="card-meta">
            <p class="error-text">{{ errors.batch_episodes }}</p>
          </div>

          <div class="batch-list">
            <article
              v-for="(episode, index) in form.batch_episodes"
              :key="episode.key"
              class="batch-item"
            >
              <div class="card-top batch-item-top">
                <div>
                  <h3 class="batch-title">第{{ getBatchEpisodeNumber(index) || '-' }}集</h3>
                  <p class="card-desc">只需填写每集不同的标题和文案。</p>
                </div>
                <button
                  type="button"
                  class="ghost-action"
                  :disabled="form.batch_episodes.length <= 1"
                  @click="removeBatchEpisode(index)"
                >
                  删除
                </button>
              </div>

              <div class="card-meta form-grid two-columns">
                <div class="form-control">
                  <label class="field-label">分集标题 <span class="required-mark">*</span></label>
                  <input
                    v-model="episode.episode_title"
                    type="text"
                    class="field-input"
                    @input="handleBatchTitleInput(index)"
                    :class="{ 'field-error': getBatchEpisodeError(index, 'episode_title') }"
                    placeholder="例如：大闹天宫"
                  >
                  <p v-if="getBatchEpisodeError(index, 'episode_title')" class="error-text">
                    {{ getBatchEpisodeError(index, 'episode_title') }}
                  </p>
                </div>
                <div class="form-control">
                  <label class="field-label">分集名称</label>
                  <input
                    v-model="episode.name"
                    type="text"
                    class="field-input"
                    :placeholder="`默认：第${getBatchEpisodeNumber(index) || index + 1}集`"
                  >
                </div>
              </div>

              <div class="card-footer form-control">
                <label class="field-label">原始主题或文案 <span class="required-mark">*</span></label>
                <textarea
                  v-model="episode.original_topic"
                  class="field-input batch-textarea"
                  @input="handleBatchTopicInput(index)"
                  :class="{ 'field-error': getBatchEpisodeError(index, 'original_topic') }"
                  placeholder="请输入这一集的原始文案或剧情简介..."
                ></textarea>
                <p v-if="getBatchEpisodeError(index, 'original_topic')" class="error-text">
                  {{ getBatchEpisodeError(index, 'original_topic') }}
                </p>
              </div>
            </article>
          </div>

          <div class="batch-actions-bottom">
            <button type="button" class="secondary-action" @click="addBatchEpisode">新增一集</button>
          </div>
        </div>

        <div class="submit-bar">
          <button type="button" class="ghost-link" @click="goBack" :disabled="submitting">取消</button>
          <button type="submit" class="primary-action" :disabled="submitting">
            <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
            <span>{{ submitLabel }}</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import { promptSetAPI } from '@/api/prompts';

const DEFAULT_EPISODE_NAME_REGEX = /^第\d+集$/;

const createBatchEpisode = () => ({
  key: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  episode_title: '',
  name: '',
  original_topic: '',
  titleTouched: false,
});

export default {
  name: 'ProjectCreate',
  data() {
    return {
      form: {
        mode: 'single',
        series: null,
        episode_number: 1,
        episode_title: '',
        name: '',
        description: '',
        original_topic: '',
        prompt_template_set: null,
        start_episode_number: 1,
        batch_episodes: [createBatchEpisode()],
      },
      errors: {
        original_topic: '',
        start_episode_number: '',
        batch_episodes: '',
        batch_episode_errors: {},
      },
      templateSets: [],
      loadingTemplates: false,
      submitting: false,
      submitTried: false,
      singleTitleTouched: false,
    };
  },
  computed: {
    ...mapState('projects', ['seriesList']),
    submitLabel() {
      if (!this.submitting) {
        return this.form.mode === 'batch' ? '批量创建分集' : '创建分集';
      }
      return this.form.mode === 'batch' ? '批量创建中...' : '创建中...';
    },
  },
  watch: {
    'form.series': {
      async handler(newValue, oldValue) {
        if (!newValue || newValue === oldValue) {
          return;
        }
        await this.applySeriesDefaults();
      },
    },
    'form.episode_number'(newValue, oldValue) {
      if (!newValue || newValue === oldValue) {
        return;
      }

      const currentName = (this.form.name || '').trim();
      if (!currentName || DEFAULT_EPISODE_NAME_REGEX.test(currentName)) {
        this.form.name = `第${newValue}集`;
      }
    },
  },
  async created() {
    if (this.$route.query.mode === 'batch') {
      this.form.mode = 'batch';
    }
    await this.fetchSeries();
    if (this.$route.query.series_id) {
      this.form.series = this.$route.query.series_id;
    }
    await this.fetchTemplateSets();
    await this.applySeriesDefaults();
  },
  methods: {
    ...mapActions('projects', ['createProject', 'batchCreateProjects', 'fetchSeries', 'fetchSeriesDetail']),
    async fetchTemplateSets() {
      this.loadingTemplates = true;
      try {
        const response = await promptSetAPI.getList({ is_active: true, page_size: 100 });
        this.templateSets = response.results || response || [];
      } finally {
        this.loadingTemplates = false;
      }
    },
    getLatestEpisode(episodes = []) {
      if (!episodes.length) {
        return null;
      }

      return [...episodes].sort((left, right) => {
        const leftOrder = left.sort_order || left.episode_number || 0;
        const rightOrder = right.sort_order || right.episode_number || 0;

        if (leftOrder !== rightOrder) {
          return rightOrder - leftOrder;
        }

        const leftTime = new Date(left.created_at || 0).getTime();
        const rightTime = new Date(right.created_at || 0).getTime();
        return rightTime - leftTime;
      })[0];
    },
    async applySeriesDefaults() {
      if (!this.form.series) {
        this.form.episode_number = 1;
        this.form.start_episode_number = 1;
        this.form.name = '第1集';
        this.form.prompt_template_set = null;
        return;
      }

      try {
        const series = await this.fetchSeriesDetail(this.form.series);
        const latestEpisode = this.getLatestEpisode(series?.episodes || []);
        const nextEpisodeNumber = latestEpisode
          ? ((latestEpisode.episode_number || latestEpisode.sort_order || 0) + 1)
          : 1;

        this.form.episode_number = nextEpisodeNumber;
        this.form.start_episode_number = nextEpisodeNumber;
        this.form.name = `第${nextEpisodeNumber}集`;
        this.form.prompt_template_set = latestEpisode?.prompt_template_set || null;
      } catch (error) {
        console.error('Failed to apply series defaults:', error);
      }
    },
    switchMode(mode) {
      if (this.form.mode === mode) {
        return;
      }
      this.form.mode = mode;
      this.resetErrors();
    },
    resetErrors() {
      this.errors = {
        original_topic: '',
        start_episode_number: '',
        batch_episodes: '',
        batch_episode_errors: {},
      };
    },
    addBatchEpisode() {
      this.form.batch_episodes.push(createBatchEpisode());
    },
    removeBatchEpisode(index) {
      if (this.form.batch_episodes.length <= 1) {
        return;
      }
      this.form.batch_episodes.splice(index, 1);
    },
    getBatchEpisodeNumber(index) {
      const start = Number(this.form.start_episode_number) || 0;
      if (!start) {
        return null;
      }
      return start + index;
    },
    getBatchEpisodeError(index, field) {
      return this.errors.batch_episode_errors?.[index]?.[field] || '';
    },
    buildEpisodeTitleFromTopic(value) {
      return (value || '').replace(/\s+/g, ' ').trim().slice(0, 8);
    },
    handleSingleTitleInput() {
      this.singleTitleTouched = !!this.form.episode_title.trim();
    },
    handleSingleTopicInput() {
      if (this.singleTitleTouched && this.form.episode_title.trim()) {
        return;
      }
      this.form.episode_title = this.buildEpisodeTitleFromTopic(this.form.original_topic);
      this.singleTitleTouched = false;
    },
    handleBatchTitleInput(index) {
      const episode = this.form.batch_episodes[index];
      if (!episode) {
        return;
      }
      episode.titleTouched = !!episode.episode_title.trim();
    },
    handleBatchTopicInput(index) {
      const episode = this.form.batch_episodes[index];
      if (!episode) {
        return;
      }
      if (episode.titleTouched && episode.episode_title.trim()) {
        return;
      }
      episode.episode_title = this.buildEpisodeTitleFromTopic(episode.original_topic);
      episode.titleTouched = false;
    },
    validateCommonFields() {
      if (!this.form.series) {
        alert('请选择所属作品');
        return false;
      }
      return true;
    },
    validateSingleForm() {
      if (!this.validateCommonFields()) {
        return false;
      }
      if (!this.form.episode_number || this.form.episode_number < 1) {
        alert('请输入有效的分集序号');
        return false;
      }
      if (!this.form.episode_title.trim()) {
        alert('请输入分集标题');
        return false;
      }
      if (!this.form.original_topic.trim()) {
        this.errors.original_topic = '请输入原始主题或文案';
        return false;
      }
      return true;
    },
    validateBatchForm() {
      if (!this.validateCommonFields()) {
        return false;
      }
      if (!this.form.start_episode_number || this.form.start_episode_number < 1) {
        this.errors.start_episode_number = '请输入有效的起始分集序号';
        return false;
      }
      if (!Array.isArray(this.form.batch_episodes) || this.form.batch_episodes.length === 0) {
        this.errors.batch_episodes = '请至少添加一个分集';
        return false;
      }

      let hasError = false;
      const batchEpisodeErrors = {};
      this.form.batch_episodes.forEach((episode, index) => {
        const itemErrors = {};
        if (!episode.episode_title.trim()) {
          itemErrors.episode_title = '请输入分集标题';
          hasError = true;
        }
        if (!episode.original_topic.trim()) {
          itemErrors.original_topic = '请输入原始主题或文案';
          hasError = true;
        }
        if (Object.keys(itemErrors).length) {
          batchEpisodeErrors[index] = itemErrors;
        }
      });

      if (hasError) {
        this.errors.batch_episode_errors = batchEpisodeErrors;
        this.errors.batch_episodes = '请补全每个分集的标题和文案';
        return false;
      }
      return true;
    },
    validateForm() {
      this.submitTried = true;
      this.resetErrors();
      if (this.form.mode === 'batch') {
        return this.validateBatchForm();
      }
      return this.validateSingleForm();
    },
    async handleSubmit() {
      if (!this.validateForm()) {
        return;
      }
      this.submitting = true;
      try {
        if (this.form.mode === 'batch') {
          const response = await this.batchCreateProjects({
            series: this.form.series,
            description: this.form.description.trim(),
            prompt_template_set: this.form.prompt_template_set,
            start_episode_number: this.form.start_episode_number,
            episodes: this.form.batch_episodes.map((episode) => ({
              episode_title: episode.episode_title.trim(),
              name: episode.name.trim(),
              original_topic: episode.original_topic.trim(),
            })),
          });
          this.$message.success(`已成功创建 ${response.count || response.results?.length || 0} 集`);
          this.goBack();
          return;
        }

        const project = await this.createProject({
          series: this.form.series,
          episode_number: this.form.episode_number,
          episode_title: this.form.episode_title.trim(),
          name: this.form.name.trim(),
          description: this.form.description.trim(),
          original_topic: this.form.original_topic.trim(),
          prompt_template_set: this.form.prompt_template_set,
          sort_order: this.form.episode_number,
        });
        this.$router.push({ name: 'ProjectDetail', params: { id: project.id } });
      } catch (error) {
        const errorMsg = error.response?.data?.message || error.response?.data?.detail || error.message || '创建分集失败';
        alert(errorMsg);
      } finally {
        this.submitting = false;
      }
    },
    goBack() {
      if (this.form.series) {
        this.$router.push({ name: 'SeriesDetail', params: { id: this.form.series } });
        return;
      }
      this.$router.push({ name: 'SeriesList' });
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

.card-block {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%)
      0 0 / 100% 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .card-block {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%)
      0 0 / 100% 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.form-layout {
  max-width: 1120px;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.75rem;
}

.card-block {
  padding: 1.25rem;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card-block:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 40px rgba(15, 23, 42, 0.12);
}

.layout-shell.theme-dark .card-block:hover {
  box-shadow: 0 22px 40px rgba(2, 6, 23, 0.65);
}

.mode-section {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.card-top,
.card-meta,
.card-footer {
  display: flex;
  gap: 1rem;
}

.card-top {
  justify-content: space-between;
  align-items: flex-start;
}

.card-meta,
.card-footer {
  margin-top: 1rem;
}

.card-title,
.batch-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .card-title,
.layout-shell.theme-dark .batch-title {
  color: #e2e8f0;
}

.card-desc,
.helper-text {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.mode-switch {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}

.mode-option,
.secondary-action,
.ghost-action,
.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-option,
.secondary-action,
.primary-action {
  padding: 0.75rem 1.5rem;
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
}

.layout-shell.theme-dark .mode-option,
.layout-shell.theme-dark .secondary-action,
.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.mode-option.active,
.mode-option:hover,
.secondary-action:hover,
.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.ghost-action,
.ghost-link {
  border: none;
  background: transparent;
  color: #64748b;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
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
  gap: 0.5rem;
}

.form-control--hint {
  justify-content: center;
}

.field-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
}

.layout-shell.theme-dark .field-label {
  color: #e2e8f0;
}

.required-mark {
  color: #ef4444;
}

.field-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.2s ease;
  outline: none;
}

.layout-shell.theme-dark .field-input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.field-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.field-textarea {
  min-height: 220px;
  resize: vertical;
}

.batch-textarea {
  min-height: 160px;
  resize: vertical;
}

.field-error {
  border-color: rgba(239, 68, 68, 0.6);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12);
}

.error-text {
  margin: 0;
  color: #ef4444;
  font-size: 0.85rem;
}

.batch-list {
  display: grid;
  gap: 1rem;
  margin-top: 1rem;
}

.batch-item {
  padding: 1rem 0 0;
  border-top: 1px dashed rgba(148, 163, 184, 0.28);
}

.batch-item:first-child {
  padding-top: 0;
  border-top: none;
}

.layout-shell.theme-dark .batch-item {
  border-top-color: rgba(148, 163, 184, 0.2);
}

.batch-item-top {
  align-items: center;
}

.batch-actions-bottom {
  display: flex;
  justify-content: center;
  margin-top: 1.25rem;
}

.submit-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1rem;
  margin-top: 0.5rem;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .two-columns {
    grid-template-columns: 1fr;
  }

  .submit-bar,
  .card-top {
    flex-direction: column;
    align-items: stretch;
  }

  .primary-action,
  .secondary-action,
  .mode-option {
    width: 100%;
  }
}
</style>
