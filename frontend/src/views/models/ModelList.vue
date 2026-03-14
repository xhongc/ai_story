<template>
  <div class="page-shell model-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">
          模型管理
        </h1>
        <p class="page-subtitle">
          管理模型提供商与运行状态
        </p>
      </div>
      <button
        class="primary-action"
        @click="handleCreate"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        <span>添加模型</span>
      </button>
    </div>

    <div class="filter-card">
      <div class="search-box">
        <svg
          class="search-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索模型名称..."
          class="search-input"
          @input="handleSearch"
        >
      </div>
      <div class="status-filters">
        <button
          v-for="option in providerTypeOptions"
          :key="option.value"
          :class="['status-filter-btn', { active: filters.provider_type === option.value }]"
          @click="handleTypeFilter(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
      <div class="status-filters">
        <button
          v-for="option in statusOptions"
          :key="option.value"
          :class="['status-filter-btn', { active: filters.is_active === option.value }]"
          @click="handleStatusFilter(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <loading-container
      :loading="loading"
      class="loading-container"
    >
      <div
        v-if="providers.length === 0"
        class="empty-state"
      >
        <svg
          class="empty-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
        <p class="empty-text">
          暂无模型
        </p>
        <p class="empty-hint">
          添加模型提供商后即可在项目中使用
        </p>
        <button
          class="secondary-action"
          @click="handleCreate"
        >
          添加模型
        </button>
      </div>

      <div
        v-else
        class="card-grid"
      >
        <article
          v-for="provider in providers"
          :key="provider.id"
          class="data-card"
          @click="handleEdit(provider)"
        >
          <div class="card-header">
            <div>
              <h3 class="card-title">
                {{ provider.name }}
              </h3>
              <p class="card-subtitle">
                {{ provider.model_name }}
              </p>
            </div>
            <span
              class="badge badge-sm"
              :class="getProviderTypeBadgeClass(provider.provider_type)"
            >
              {{ getProviderTypeLabel(provider.provider_type) }}
            </span>
          </div>

          <div class="card-body">
            <div class="meta-row">
              <span class="meta-label">优先级</span>
              <span class="meta-value">{{ provider.priority }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">状态</span>
              <span
                class="badge badge-sm"
                :class="provider.is_active ? 'badge-success' : 'badge-info'"
              >
                {{ provider.is_active ? '已激活' : '未激活' }}
              </span>
            </div>
            <div class="meta-row">
              <span class="meta-label">使用次数</span>
              <div class="usage-cell">
                <span>总计: {{ provider.total_usage_count || 0 }}</span>
                <span class="muted">近7天: {{ provider.recent_usage_count || 0 }}</span>
              </div>
            </div>
          </div>

          <div class="card-actions">
            <button
              class="ghost-action"
              :class="{ 'is-loading': testingProviderId === provider.id }"
              :disabled="!provider.is_active || testingProviderId !== null"
              @click.stop="handleTest(provider)"
            >
              <span
                v-if="testingProviderId === provider.id"
                class="action-spinner"
                aria-hidden="true"
              />
              <span>{{ testingProviderId === provider.id ? '测试中...' : '测试' }}</span>
            </button>
            <button
              class="ghost-action"
              @click.stop="handleToggleStatus(provider)"
            >
              {{ provider.is_active ? '停用' : '启用' }}
            </button>
            <button
              class="ghost-action danger"
              @click.stop="handleDelete(provider)"
            >
              删除
            </button>
          </div>
        </article>
      </div>
    </loading-container>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import LoadingContainer from '@/components/common/LoadingContainer.vue'

const MODEL_FILTER_STORAGE_KEY = 'model_list_filters'

const getSavedFilters = () => {
  const defaultFilters = {
    search: '',
    provider_type: '',
    is_active: ''
  }

  try {
    const saved = localStorage.getItem(MODEL_FILTER_STORAGE_KEY)
    if (!saved) {
      return defaultFilters
    }

    const parsed = JSON.parse(saved)
    return {
      search: typeof parsed.search === 'string' ? parsed.search : '',
      provider_type: typeof parsed.provider_type === 'string' ? parsed.provider_type : '',
      is_active: typeof parsed.is_active === 'string' ? parsed.is_active : ''
    }
  } catch (error) {
    return defaultFilters
  }
}

export default {
  name: 'ModelList',
  components: {
    LoadingContainer
  },
  data() {
    const savedFilters = getSavedFilters()

    return {
      filters: savedFilters,
      providerTypeOptions: [
        { label: '全部类型', value: '' },
        { label: 'LLM模型', value: 'llm' },
        { label: '文生图模型', value: 'text2image' },
        { label: '图生视频模型', value: 'image2video' }
      ],
      statusOptions: [
        { label: '全部状态', value: '' },
        { label: '已激活', value: 'true' },
        { label: '未激活', value: 'false' }
      ],
      searchTimer: null,
      testingProviderId: null
    }
  },
  computed: {
    ...mapState('models', {
      providers: (state) => state.providers,
      loading: (state) => state.loading.providers
    })
  },
  created() {
    this.loadProviders()
  },
  beforeDestroy() {
    clearTimeout(this.searchTimer)
  },
  methods: {
    ...mapActions('models', [
      'fetchProviders',
      'deleteProvider',
      'toggleProviderStatus',
      'testProviderConnection'
    ]),

    async loadProviders() {
      try {
        await this.fetchProviders(this.getFilterParams())
      } catch (error) {
        console.error('加载模型提供商列表失败:', error)
        this.$message?.error('加载模型列表失败')
      }
    },

    getFilterParams() {
      const params = {}
      if (this.filters.search) {
        params.search = this.filters.search
      }
      if (this.filters.provider_type) {
        params.provider_type = this.filters.provider_type
      }
      if (this.filters.is_active !== '') {
        params.is_active = this.filters.is_active === 'true'
      }
      return params
    },

    persistFilters() {
      try {
        localStorage.setItem(MODEL_FILTER_STORAGE_KEY, JSON.stringify(this.filters))
      } catch (error) {
        console.error('保存模型筛选条件失败:', error)
      }
    },

    handleFilter() {
      this.persistFilters()
      this.loadProviders()
    },

    handleSearch() {
      clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => {
        this.handleFilter()
      }, 500)
    },

    handleTypeFilter(value) {
      this.filters.provider_type = value
      this.handleFilter()
    },

    handleStatusFilter(value) {
      this.filters.is_active = value
      this.handleFilter()
    },

    handleCreate() {
      this.$router.push({ name: 'model-create' })
    },

    handleEdit(provider) {
      this.$router.push({ name: 'model-edit', params: { id: provider.id } })
    },

    async handleToggleStatus(provider) {
      try {
        await this.toggleProviderStatus(provider.id)
        this.$message?.success(`模型已${provider.is_active ? '停用' : '启用'}`)
      } catch (error) {
        console.error('切换模型状态失败:', error)
        this.$message?.error('切换状态失败')
      }
    },

    async handleTest(provider) {
      this.testingProviderId = provider.id
      try {
        const result = await this.testProviderConnection({
          id: provider.id,
          testPrompt: 'Hello, this is a test.'
        })

        if (result.success) {
          await this.$alert(`测试成功! 延迟: ${result.latency_ms}ms`, '测试结果', { tone: 'success' })
        } else {
          await this.$alert(`测试失败: ${result.error}`, '测试结果', { tone: 'error' })
        }
      } catch (error) {
        console.error('测试连接失败:', error)
        await this.$alert('测试连接失败', '测试结果', { tone: 'error' })
      } finally {
        this.testingProviderId = null
      }
    },

    async handleDelete(provider) {
      const confirmed = await this.$confirm(
        `确定要删除模型 "${provider.name}" 吗?`,
        '删除模型',
        { tone: 'danger', confirmText: '删除' }
      )

      if (!confirmed) {
        return
      }

      try {
        await this.deleteProvider(provider.id)
        await this.$alert('删除成功', '操作完成', { tone: 'success' })
      } catch (error) {
        console.error('删除模型失败:', error)
        await this.$alert(
          error.response?.data?.error || '删除失败,该模型可能正在被项目使用',
          '删除失败',
          { tone: 'error' }
        )
      }
    },

    getProviderTypeLabel(type) {
      const labels = {
        llm: 'LLM',
        text2image: '文生图',
        image2video: '图生视频'
      }
      return labels[type] || type
    },

    getProviderTypeBadgeClass(type) {
      const classes = {
        llm: 'badge-primary',
        text2image: 'badge-info',
        image2video: 'badge-accent'
      }
      return classes[type] || 'badge-ghost'
    }
  }
}
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: 2.5rem 3.5rem 3rem;
  background: transparent;
}

.loading-container {
  display: block;
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

.page-title {
  font-size: 2.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.primary-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .primary-action:hover {
  border-color: rgba(94, 234, 212, 0.6);
  box-shadow: 0 12px 24px rgba(2, 6, 23, 0.55);
}

.primary-action:active {
  transform: translateY(0);
}

.filter-card {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem 1.25rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  margin-bottom: 2.5rem;
  backdrop-filter: blur(10px);
}

.layout-shell.theme-dark .filter-card {
  background: rgba(15, 23, 42, 0.86);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 280px;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.25rem;
  height: 1.25rem;
  color: #94a3b8;
  pointer-events: none;
}

.layout-shell.theme-dark .search-icon {
  color: #94a3b8;
}

.search-input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 3rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .search-input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.search-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.search-input::placeholder {
  color: #cbd5e1;
}

.layout-shell.theme-dark .search-input::placeholder {
  color: #64748b;
}

.status-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-filter-btn {
  padding: 0.625rem 1.25rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .status-filter-btn {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #cbd5e1;
}

.status-filter-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.layout-shell.theme-dark .status-filter-btn:hover {
  border-color: rgba(148, 163, 184, 0.4);
  background: rgba(30, 41, 59, 0.9);
}

.status-filter-btn.active {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  border-color: rgba(20, 184, 166, 0.5);
}

.layout-shell.theme-dark .status-filter-btn.active {
  background: rgba(94, 234, 212, 0.2);
  color: #e2e8f0;
  border-color: rgba(94, 234, 212, 0.5);
}

.card-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

@media (min-width: 640px) {
  .card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1536px) {
  .card-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

.data-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.layout-shell.theme-dark .data-card {
  background: rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
}

.data-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  border-color: rgba(148, 163, 184, 0.35);
}

.layout-shell.theme-dark .data-card:hover {
  box-shadow: 0 18px 36px rgba(2, 6, 23, 0.6);
}

.data-card:hover::before {
  transform: scaleX(1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.card-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-subtitle {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
  word-break: break-all;
  overflow-wrap: anywhere;
}

.layout-shell.theme-dark .card-subtitle {
  color: #94a3b8;
}

.card-body {
  display: grid;
  gap: 0.75rem;
}

.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.meta-label {
  color: #94a3b8;
  font-size: 0.8rem;
}

.meta-value {
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .meta-value {
  color: #e2e8f0;
}

.usage-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.2rem;
  font-size: 0.8rem;
  text-align: right;
}

.badge {
  background: rgba(148, 163, 184, 0.12);
  border-color: rgba(148, 163, 184, 0.24);
  color: #0f172a;
}

.layout-shell.theme-dark .badge {
  background: rgba(148, 163, 184, 0.16);
  border-color: rgba(148, 163, 184, 0.3);
  color: #e2e8f0;
}

.badge-info {
  background: rgba(148, 163, 184, 0.16);
  border-color: rgba(148, 163, 184, 0.35);
  color: #475569;
}

.layout-shell.theme-dark .badge-info {
  color: #bfdbfe;
}

.badge-success {
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.3);
  color: #047857;
}

.layout-shell.theme-dark .badge-success {
  color: #6ee7b7;
}

.badge-primary {
  background: rgba(20, 184, 166, 0.16);
  border-color: rgba(20, 184, 166, 0.35);
  color: #0f766e;
}

.layout-shell.theme-dark .badge-primary {
  color: #5eead4;
}

.badge-accent {
  background: rgba(14, 165, 233, 0.16);
  border-color: rgba(14, 165, 233, 0.3);
  color: #0284c7;
}

.layout-shell.theme-dark .badge-accent {
  color: #7dd3fc;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.data-card:hover .card-actions {
  opacity: 1;
}

.ghost-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ghost-action:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.layout-shell.theme-dark .ghost-action {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
}

.ghost-action:hover {
  border-color: rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.06);
}

.layout-shell.theme-dark .ghost-action:hover {
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(148, 163, 184, 0.22);
}

.ghost-action.danger {
  color: #dc2626;
}

.ghost-action.danger:hover {
  border-color: rgba(248, 113, 113, 0.35);
  background: rgba(248, 113, 113, 0.12);
  color: #dc2626;
}

.ghost-action.is-loading {
  border-color: rgba(20, 184, 166, 0.28);
  background: rgba(20, 184, 166, 0.1);
}

.layout-shell.theme-dark .ghost-action.is-loading {
  border-color: rgba(94, 234, 212, 0.32);
  background: rgba(20, 184, 166, 0.18);
}

.action-spinner {
  width: 0.85rem;
  height: 0.85rem;
  border-radius: 999px;
  border: 2px solid rgba(15, 23, 42, 0.18);
  border-top-color: currentColor;
  animation: button-spin 0.75s linear infinite;
}

.layout-shell.theme-dark .action-spinner {
  border-color: rgba(226, 232, 240, 0.2);
  border-top-color: currentColor;
}

@keyframes button-spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 6rem 2rem;
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  color: #cbd5e1;
  margin-bottom: 1.5rem;
}

.layout-shell.theme-dark .empty-icon {
  color: #475569;
}

.empty-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.layout-shell.theme-dark .empty-text {
  color: #e2e8f0;
}

.empty-hint {
  color: #94a3b8;
  margin: 0 0 2rem 0;
}

.secondary-action {
  padding: 0.875rem 2rem;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .secondary-action {
  background: #e2e8f0;
  color: #0f172a;
}

.secondary-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
}

.muted {
  color: #94a3b8;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1.5rem;
  }

  .primary-action {
    width: 100%;
    justify-content: center;
  }
}
</style>
