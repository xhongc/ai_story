<template>
  <div class="page-shell prompt-debug-workbench">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">提示词调试工作台</h1>
        <p class="page-subtitle">围绕模板进行调试、联动与保存</p>
      </div>
      <div class="page-actions">
        <button class="secondary-action" @click="goBack">返回模板</button>
        <button class="secondary-action" @click="handleSaveTemplate" :disabled="debugLoading">保存到当前模板</button>
        <button class="primary-action" @click="handleSaveAsVersion" :disabled="debugLoading">另存为新版本</button>
      </div>
    </div>

    <LoadingContainer :loading="loadingPage">
      <div v-if="session" class="workbench-grid">
        <section class="workbench-card editor-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">模板草稿</h2>
              <p class="card-desc">当前阶段：{{ stageLabel(session.stage_type) }}</p>
            </div>
            <span class="pill pill-primary">{{ session.prompt_template_detail?.stage_type_display }}</span>
          </div>

          <div class="field-group">
            <label class="field-label">模型</label>
            <select v-model="form.model_provider_id" class="field-select">
              <option value="">使用默认模型</option>
              <option v-for="item in availableProviders" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </div>

          <div class="field-group">
            <label class="field-label">模板内容</label>
            <textarea v-model="form.template_content" class="field-textarea textarea-lg" rows="14" />
          </div>
          <div class="field-group">
            <label class="field-label">阶段输入</label>
            <textarea v-model="inputPayloadText" class="field-textarea" rows="8" :placeholder="inputPlaceholder" />
          </div>

          <div class="field-group">
            <label class="field-label">变量值 JSON</label>
            <textarea v-model="variableValuesText" class="field-textarea" rows="8" placeholder='{"topic":"赛博都市"}' />
          </div>

          <div v-if="canSelectSource" class="field-group">
            <label class="field-label">上游调试资产</label>
            <select v-model="form.source_artifact_id" class="field-select">
              <option value="">不使用上游资产</option>
              <option v-for="item in sourceArtifacts" :key="item.id" :value="item.id">
                {{ item.name }} · {{ artifactTypeLabel(item.artifact_type) }}
              </option>
            </select>
          </div>

          <div class="editor-actions">
            <button class="primary-action" @click="handleRun" :disabled="debugLoading">运行调试</button>
          </div>
        </section>

        <section class="workbench-card result-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">本次结果</h2>
              <p class="card-desc">运行后自动保存结果与联动资产</p>
            </div>
            <span v-if="debugLoading && isLlmStage" class="streaming-pill">流式生成中</span>
          </div>

          <div v-if="displayRun" class="result-blocks">
            <div class="result-block">
              <h3>渲染后 Prompt</h3>
              <pre>{{ displayRun.rendered_prompt }}</pre>
            </div>
            <div class="result-block" v-if="isLlmStage">
              <h3>流式输出</h3>
              <pre>{{ displayRun.streamed_text || displayRun.raw_response?.text || '' }}</pre>
            </div>
            <div class="result-block" v-if="displayRun.parsed_output">
              <h3>结构化输出</h3>
              <pre>{{ formatJson(displayRun.parsed_output) }}</pre>
            </div>
            <div class="result-block" v-if="displayRun.raw_response && !isLlmStage">
              <h3>原始响应</h3>
              <pre>{{ formatJson(displayRun.raw_response) }}</pre>
            </div>
            <div class="result-block" v-if="displayRun.error_message">
              <h3>错误信息</h3>
              <pre>{{ displayRun.error_message }}</pre>
            </div>
          </div>
          <div v-else class="empty-state compact-empty">
            <div class="empty-hero">还没有调试结果</div>
            <p class="empty-hint">先运行一次调试，结果会沉淀为可复用资产</p>
          </div>
        </section>

        <section class="workbench-card history-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">运行历史</h2>
              <p class="card-desc">最近 5 次运行</p>
            </div>
          </div>
          <div v-if="debugRuns.length" class="history-list">
            <article
              v-for="run in debugRuns"
              :key="run.id"
              :class="['history-item', { active: run.id === selectedRunId }]"
              role="button"
              tabindex="0"
              @click="selectRun(run)"
              @keyup.enter="selectRun(run)"
            >
              <div class="card-meta">
                <div class="meta-item">
                  <span class="meta-label">状态</span>
                  <span class="meta-value">{{ run.status }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">延迟</span>
                  <span class="meta-value">{{ run.latency_ms }}ms</span>
                </div>
              </div>
              <div class="card-footer">
                <span class="meta-time">{{ formatDate(run.created_at) }}</span>
                <button class="ghost-action" type="button" @click.stop="selectRun(run)">查看</button>
              </div>
            </article>
          </div>
          <div v-else class="empty-state compact-empty">
            <p class="empty-hint">暂无运行历史</p>
          </div>
        </section>

        <section class="workbench-card asset-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">联动资产</h2>
              <p class="card-desc">分镜、图片、视频都可以继续给下游阶段使用</p>
            </div>
          </div>
          <div v-if="sessionArtifacts.length" class="asset-list">
            <article v-for="item in sessionArtifacts" :key="item.id" class="asset-item">
              <div class="card-meta">
                <div class="meta-item">
                  <span class="meta-label">类型</span>
                  <span class="meta-value">{{ artifactTypeLabel(item.artifact_type) }}</span>
                </div>
                <div class="meta-item" v-if="item.sequence_number">
                  <span class="meta-label">序号</span>
                  <span class="meta-value">{{ item.sequence_number }}</span>
                </div>
              </div>
              <div class="asset-preview" v-if="item.preview_image_url">
                <img :src="item.preview_image_url" :alt="item.name">
              </div>
              <div class="asset-preview-text">{{ item.preview_text || item.name }}</div>
            </article>
          </div>
          <div v-else class="empty-state compact-empty">
            <p class="empty-hint">暂无联动资产</p>
          </div>
        </section>
      </div>
    </LoadingContainer>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex'
import LoadingContainer from '@/components/common/LoadingContainer.vue'
import { formatDate } from '@/utils/helpers'

const STAGE_LABELS = {
  rewrite: 'LLM 阶段',
  storyboard: 'LLM 阶段',
  camera_movement: 'LLM 阶段',
  image_generation: '文生图',
  video_generation: '图生视频'
}

const ARTIFACT_LABELS = {
  text: '文本',
  storyboard_bundle: '分镜集合',
  storyboard_item: '单条分镜',
  image: '图片',
  video: '视频'
}

export default {
  name: 'PromptDebugWorkbench',
  components: {
    LoadingContainer,
  },
  data() {
    return {
      loadingPage: false,
      form: {
        template_content: '',
        model_provider_id: '',
        source_artifact_id: '',
      },
      variableValuesText: '{}',
      inputPayloadText: '',
      lastRun: null,
      streamingRun: null,
      availableProviders: [],
      linkedArtifacts: [],
      sessionArtifacts: [],
    }
  },
  computed: {
    ...mapState('prompts', {
      session: state => state.currentDebugSession,
      debugRuns: state => state.debugRuns,
      debugArtifacts: state => state.debugArtifacts,
      debugLoading: state => state.debugLoading,
    }),
    sourceArtifacts() {
      return this.linkedArtifacts
    },
    isLlmStage() {
      return ['rewrite', 'storyboard', 'camera_movement'].includes(this.session?.stage_type)
    },
    displayRun() {
      return this.streamingRun || this.lastRun
    },
    selectedRunId() {
      return this.lastRun?.id || ''
    },
    canSelectSource() {
      return ['image_generation', 'video_generation'].includes(this.session?.stage_type)
    },
    inputPlaceholder() {
      const stageType = this.session?.stage_type
      if (stageType === 'image_generation') {
        return '{"negative_prompt":"低质量","ratio":"1:1"}'
      }
      if (stageType === 'video_generation') {
        return '{"image_url":"https://...","duration":5,"fps":24}'
      }
      return '请输入用户提示词文本'
    },
  },
  async created() {
    await this.bootstrap()
  },
  methods: {
    ...mapActions('prompts', [
      'bootstrapDebugSession',
      'fetchDebugSession',
      'runDebugSession',
      'runDebugSessionStream',
      'fetchDebugArtifacts',
      'saveDebugTemplate',
      'saveDebugTemplateAsVersion',
    ]),
    ...mapActions('models', ['fetchProviders']),
    formatDate,
    stageLabel(stageType) {
      return STAGE_LABELS[stageType] || stageType
    },
    artifactTypeLabel(type) {
      return ARTIFACT_LABELS[type] || type
    },
    formatJson(value) {
      return JSON.stringify(value || {}, null, 2)
    },
    parseJsonText(text, fallback = {}) {
      try {
        return text ? JSON.parse(text) : fallback
      } catch (error) {
        throw new Error('JSON 格式不正确')
      }
    },

    parseInputPayload() {
      if (this.isLlmStage) {
        return this.inputPayloadText || ''
      }
      return this.parseJsonText(this.inputPayloadText, {})
    },
    async bootstrap() {
      this.loadingPage = true
      try {
        const templateId = this.$route.params.id
        const session = await this.bootstrapDebugSession(templateId)
        this.form.template_content = session.draft_template_content || session.prompt_template_detail?.template_content || ''
        this.form.model_provider_id = session.prompt_template_detail?.model_provider || session.model_provider || ''
        this.form.source_artifact_id = session.latest_source_artifact || ''
        this.variableValuesText = this.formatJson(session.latest_variable_values || {})
        this.inputPayloadText = this.isLlmStage
          ? (typeof session.latest_input_payload === 'string' ? session.latest_input_payload : '')
          : this.formatJson(session.latest_input_payload || {})
        const sessionArtifacts = await this.fetchDebugArtifacts({ session_id: session.id })
        this.sessionArtifacts = sessionArtifacts.results || sessionArtifacts || []
        const providers = await this.fetchProviders({ provider_type: this.providerTypeByStage(session.stage_type), is_active: true })
        this.availableProviders = providers.results || providers || []
        await this.loadLinkedArtifacts(session)
        this.lastRun = this.debugRuns[0] || null
      } catch (error) {
        console.error('初始化调试工作台失败:', error)
        this.$message?.error('初始化调试工作台失败')
      } finally {
        this.loadingPage = false
      }
    },
    providerTypeByStage(stageType) {
      if (['rewrite', 'storyboard', 'camera_movement'].includes(stageType)) {
        return 'llm'
      }
      if (stageType === 'image_generation') {
        return 'text2image'
      }
      if (stageType === 'video_generation') {
        return 'image2video'
      }
      return ''
    },
    goBack() {
      this.$router.push(`/prompts/templates/${this.$route.params.id}/edit`)
    },
    selectRun(run) {
      this.lastRun = run
    },
    async handleRun() {
      try {
        const data = {
          template_content: this.form.template_content,
          variable_values: this.parseJsonText(this.variableValuesText, {}),
          input_payload: this.parseInputPayload(),
          source_artifact_id: this.form.source_artifact_id || null,
          model_provider_id: this.form.model_provider_id || null,
        }

        if (this.isLlmStage) {
          this.streamingRun = {
            rendered_prompt: '',
            streamed_text: '',
            parsed_output: null,
            raw_response: null,
            error_message: '',
            status: 'running',
          }
          await this.runDebugSessionStream({
            id: this.session.id,
            data,
            onEvent: this.handleStreamEvent,
          })
          await this.fetchDebugSession(this.session.id)
          const sessionArtifacts = await this.fetchDebugArtifacts({ session_id: this.session.id })
          this.sessionArtifacts = sessionArtifacts.results || sessionArtifacts || []
          await this.loadLinkedArtifacts(this.session)
          this.lastRun = this.debugRuns[0] || this.lastRun
          this.streamingRun = null
          this.$message?.success('流式调试完成')
          return
        }

        const run = await this.runDebugSession({
          id: this.session.id,
          data,
        })
        this.lastRun = run
        await this.fetchDebugSession(this.session.id)
        const sessionArtifacts = await this.fetchDebugArtifacts({ session_id: this.session.id })
        this.sessionArtifacts = sessionArtifacts.results || sessionArtifacts || []
        await this.loadLinkedArtifacts(this.session)
        this.$message?.success('调试运行完成')
      } catch (error) {
        console.error('调试运行失败:', error)
        this.$message?.error(error.response?.data?.error || error.message || '调试运行失败')
      }
    },

    handleStreamEvent(event) {
      if (!event) return
      if (!this.streamingRun) {
        this.streamingRun = {
          rendered_prompt: '',
          streamed_text: '',
          parsed_output: null,
          raw_response: null,
          error_message: '',
          status: 'running',
        }
      }

      if (event.type === 'run_started') {
        this.streamingRun = {
          ...this.streamingRun,
          rendered_prompt: event.rendered_prompt || '',
          status: 'running',
        }
        return
      }

      if (event.type === 'token') {
        this.streamingRun = {
          ...this.streamingRun,
          streamed_text: event.full_text || `${this.streamingRun.streamed_text}${event.content || ''}`,
          raw_response: {
            text: event.full_text || `${this.streamingRun.streamed_text}${event.content || ''}`,
          },
          status: 'running',
        }
        return
      }

      if (event.type === 'done') {
        this.streamingRun = {
          ...this.streamingRun,
          streamed_text: event.full_text || this.streamingRun.streamed_text,
          raw_response: {
            text: event.full_text || this.streamingRun.streamed_text,
          },
          parsed_output: event.parsed_output || null,
          latency_ms: event.latency_ms || 0,
          status: 'completed',
        }
        return
      }

      if (event.type === 'error') {
        this.streamingRun = {
          ...this.streamingRun,
          error_message: event.error || '流式调试失败',
          status: 'failed',
        }
      }
    },
    async loadLinkedArtifacts(session) {
      if (!session) {
        this.linkedArtifacts = []
        return
      }
      if (session.stage_type === 'image_generation') {
        const response = await this.fetchDebugArtifacts({ stage_type: 'storyboard', artifact_type: 'storyboard_item' })
        this.linkedArtifacts = response.results || response || []
        return
      }
      if (session.stage_type === 'video_generation') {
        const response = await this.fetchDebugArtifacts({ stage_type: 'image_generation', artifact_type: 'image' })
        this.linkedArtifacts = response.results || response || []
        return
      }
      this.linkedArtifacts = []
    },

    async handleSaveTemplate() {
      try {
        await this.saveDebugTemplate({
          id: this.session.id,
          data: {
            template_content: this.form.template_content,
            variables: this.session.draft_variables || {},
            model_provider_id: this.form.model_provider_id || null,
          },
        })
        this.$message?.success('已保存到当前模板')
      } catch (error) {
        console.error('保存模板失败:', error)
        this.$message?.error(error.response?.data?.error || '保存模板失败')
      }
    },
    async handleSaveAsVersion() {
      try {
        const response = await this.saveDebugTemplateAsVersion({
          id: this.session.id,
          data: {
            template_content: this.form.template_content,
            variables: this.session.draft_variables || {},
            model_provider_id: this.form.model_provider_id || null,
          },
        })
        this.$message?.success('已另存为新版本')
        this.$router.replace(`/prompts/templates/${response.id}/debug`)
      } catch (error) {
        console.error('另存版本失败:', error)
        this.$message?.error(error.response?.data?.error || '另存版本失败')
      }
    },
  },
  watch: {
    '$route.params.id': {
      immediate: false,
      async handler() {
        await this.bootstrap()
      },
    },
  },
}
</script>

<style scoped>
.prompt-debug-workbench {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.primary-action,
.secondary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  font-weight: 500;
  line-height: 1;
  transition: all 0.2s ease;
  cursor: pointer;
}

.primary-action {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
}

.secondary-action {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
}

.primary-action:hover,
.secondary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.primary-action:disabled,
.secondary-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.workbench-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 20px;
}

.workbench-card {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.workbench-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.14);
  border-color: rgba(34, 211, 238, 0.35);
}

.workbench-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  border-radius: 18px 18px 0 0;
  background: linear-gradient(90deg, #22d3ee 0%, #60a5fa 50%, #a78bfa 100%);
}

.editor-card,
.result-card,
.history-card,
.asset-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-card,
.asset-card {
  grid-column: span 1;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 13px;
  color: rgba(15, 23, 42, 0.65);
  font-weight: 600;
}

.card-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.75rem 1rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.meta-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.meta-value {
  font-size: 0.95rem;
  color: #0f172a;
  font-weight: 600;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.meta-time {
  font-size: 0.8rem;
  color: #94a3b8;
}

.ghost-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ghost-action:hover {
  border-color: rgba(15, 23, 42, 0.1);
  background: rgba(15, 23, 42, 0.08);
}

.field-select,
.field-textarea {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.9);
  padding: 12px 14px;
  color: #0f172a;
}

.textarea-lg {
  min-height: 320px;
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
}

.result-blocks,
.history-list,
.asset-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-block,
.history-item,
.asset-item {
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 14px;
}

.history-item {
  cursor: pointer;
}

.history-item.active {
  border-color: rgba(34, 211, 238, 0.35);
  background: rgba(34, 211, 238, 0.08);
  box-shadow: 0 12px 24px rgba(34, 211, 238, 0.12);
}

.history-item.active .meta-value,
.history-item.active .meta-time {
  color: #0f172a;
}

.history-item:focus-visible {
  outline: 2px solid rgba(34, 211, 238, 0.5);
  outline-offset: 2px;
}

.result-block pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  max-height: 260px;
  overflow: auto;
}

.asset-preview img {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 12px;
}

.asset-preview-text {
  font-size: 13px;
  color: rgba(15, 23, 42, 0.72);
  line-height: 1.6;
}

.compact-empty {
  min-height: 160px;
}

@media (max-width: 1080px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}

:global(.dark) .workbench-card {
  background: rgba(15, 23, 42, 0.82);
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 40px rgba(2, 8, 23, 0.36);
}

:global(.dark) .primary-action,
:global(.dark) .secondary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

:global(.dark) .primary-action:hover,
:global(.dark) .secondary-action:hover {
  border-color: rgba(94, 234, 212, 0.5);
  box-shadow: 0 12px 24px rgba(94, 234, 212, 0.12);
}

:global(.dark) .field-select,
:global(.dark) .field-textarea,
:global(.dark) .result-block,
:global(.dark) .history-item,
:global(.dark) .asset-item {
  background: rgba(15, 23, 42, 0.72);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.18);
}

:global(.dark) .card-meta {
  background: rgba(30, 41, 59, 0.6);
}

:global(.dark) .meta-value {
  color: #e2e8f0;
}

:global(.dark) .ghost-action {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
}

:global(.dark) .ghost-action:hover {
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(148, 163, 184, 0.22);
}

:global(.dark) .history-item.active {
  border-color: rgba(103, 232, 249, 0.32);
  background: rgba(34, 211, 238, 0.14);
  box-shadow: 0 12px 24px rgba(34, 211, 238, 0.12);
}

:global(.dark) .history-item.active .meta-value,
:global(.dark) .history-item.active .meta-time {
  color: #e2e8f0;
}

:global(.dark) .field-label,
:global(.dark) .asset-preview-text {
  color: rgba(226, 232, 240, 0.75);
}

:global(.dark) .streaming-pill {
  background: rgba(34, 211, 238, 0.18);
  color: #e2e8f0;
  border-color: rgba(103, 232, 249, 0.32);
}
</style>
