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
      <div class="header-actions">
        <button
          class="primary-action"
          @click="handleCreate"
        >
          <span>添加模型</span>
        </button>
      </div>
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
        <div class="empty-hero">
          暂无模型
        </div>
        <p class="empty-hint">
          可在统一页面中切换内置厂商导入或自定义厂商手动添加
        </p>
        <div class="empty-actions">
          <button
            class="primary-action"
            @click="handleCreate"
          >
            添加模型
          </button>
        </div>
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
          <div class="card-top">
            <div class="card-main">
              <h3 class="card-title">
                {{ provider.name }}
              </h3>
              <p class="card-desc">
                {{ provider.model_name }}
              </p>
            </div>
            <span
              class="badge badge-sm card-type-badge"
              :class="getProviderTypeBadgeClass(provider.provider_type)"
            >
              {{ getProviderTypeLabel(provider.provider_type) }}
            </span>
          </div>

          <div class="card-meta compact-meta">
            <div class="meta-item">
              <span class="meta-label">状态</span>
              <span
                class="badge badge-sm"
                :class="provider.is_active ? 'badge-success' : 'badge-info'"
              >
                {{ provider.is_active ? '已激活' : '未激活' }}
              </span>
            </div>
            <div class="meta-item meta-item-right">
              <span class="meta-label">更新</span>
              <span class="meta-value meta-time">{{ formatDate(provider.updated_at) }}</span>
            </div>
          </div>

          <div class="card-footer">
            <div
              class="card-actions"
              @click.stop
            >
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
        { label: '图生视频模型', value: 'image2video' },
        { label: '图片编辑模型', value: 'image_edit' }
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
          testPrompt: '你好啊？'
        })

        if (result.success) {
          await this.$alert(`测试成功! 延迟: ${result.latency_ms}ms, 返回结果: ${result.response}`, '测试结果', { tone: 'success' })
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

    formatDate(value) {
      if (!value) {
        return '--'
      }
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) {
        return '--'
      }
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    },

    getProviderTypeLabel(type) {
      const labels = {
        llm: 'LLM',
        text2image: '文生图',
        image2video: '图生视频',
        image_edit: '图片编辑'
      }
      return labels[type] || type
    },

    getProviderTypeBadgeClass(type) {
      const classes = {
        llm: 'badge-primary',
        text2image: 'badge-info',
        image2video: 'badge-accent',
        image_edit: 'badge-secondary'
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

.layout-shell.theme-dark .page-title {
  color: #e2e8f0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.layout-shell.theme-dark .page-subtitle {
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.primary-action,
.secondary-outline-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-action {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
}

.layout-shell.theme-dark .primary-action {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.primary-action:hover,
.secondary-outline-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.layout-shell.theme-dark .primary-action:hover,
.layout-shell.theme-dark .secondary-outline-action:hover {
  border-color: rgba(94, 234, 212, 0.6);
  box-shadow: 0 12px 24px rgba(2, 6, 23, 0.55);
}

.secondary-outline-action {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.86);
  color: #334155;
}

.layout-shell.theme-dark .secondary-outline-action {
  background: rgba(15, 23, 42, 0.86);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
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

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 3rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  outline: none;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.data-card {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%) 0 0 / 0 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1rem 1rem 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-width: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.layout-shell.theme-dark .data-card {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%) 0 0 / 0 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  border-color: rgba(148, 163, 184, 0.35);
  background-size: 100% 3px, auto;
}

.layout-shell.theme-dark .data-card:hover {
  box-shadow: 0 18px 36px rgba(2, 6, 23, 0.6);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.card-main {
  flex: 1;
  min-width: 0;
}

.card-type-badge {
  flex-shrink: 0;
  align-self: flex-start;
  white-space: nowrap;
}

.card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-desc {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.82rem;
  word-break: break-all;
  overflow-wrap: anywhere;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.card-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
}

.layout-shell.theme-dark .card-meta {
  background: rgba(30, 41, 59, 0.6);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.meta-item-right {
  align-items: flex-end;
}

.meta-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.meta-value {
  font-size: 0.9rem;
  color: #0f172a;
  font-weight: 600;
}

.layout-shell.theme-dark .meta-value {
  color: #e2e8f0;
}

.meta-time {
  font-size: 0.8rem;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
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

.badge-secondary {
  background: rgba(168, 85, 247, 0.14);
  border-color: rgba(168, 85, 247, 0.28);
  color: #7c3aed;
}

.layout-shell.theme-dark .badge-secondary {
  color: #c4b5fd;
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
  text-align: center;
  padding: 4rem 1rem;
}

.empty-hero {
  font-size: 1.3rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .empty-hero {
  color: #e2e8f0;
}

.empty-hint {
  color: #94a3b8;
  margin: 0.6rem 0 1.6rem;
}

.empty-actions {
  display: inline-flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions,
  .empty-actions {
    width: 100%;
  }

  .primary-action,
  .secondary-outline-action {
    width: 100%;
  }

  .card-meta {
    grid-template-columns: 1fr;
  }

  .meta-item-right {
    align-items: flex-start;
  }

  .card-footer {
    justify-content: flex-start;
  }
}
</style>
