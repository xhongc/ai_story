<template>
  <div class="page-shell model-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">模型管理</h1>
        <p class="page-subtitle">管理模型提供商与运行状态</p>
      </div>
      <button class="primary-action" @click="handleCreate">添加模型</button>
    </div>

    <div class="filter-card">
      <div class="search-box">
        <svg class="search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索模型名称"
          class="search-input"
          @keyup.enter="handleFilter"
        />
      </div>
      <div class="select-group">
        <select
          v-model="filters.provider_type"
          class="select-input"
          @change="handleFilter"
        >
          <option value="">全部类型</option>
          <option value="llm">LLM模型</option>
          <option value="text2image">文生图模型</option>
          <option value="image2video">图生视频模型</option>
        </select>
        <select
          v-model="filters.is_active"
          class="select-input"
          @change="handleFilter"
        >
          <option value="">全部状态</option>
          <option value="true">已激活</option>
          <option value="false">未激活</option>
        </select>
      </div>
    </div>

    <loading-container :loading="loading" class="loading-container">
      <div v-if="providers.length === 0" class="empty-state">
        <div class="empty-hero">暂无模型</div>
        <p class="empty-hint">添加模型提供商后即可在项目中使用</p>
        <button class="secondary-action" @click="handleCreate">添加模型</button>
      </div>

      <div v-else class="card-grid">
        <article v-for="provider in providers" :key="provider.id" class="data-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">{{ provider.name }}</h3>
              <p class="card-subtitle">{{ provider.model_name }}</p>
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
                :class="provider.is_active ? 'badge-success' : 'badge-ghost'"
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
              @click="handleTest(provider)"
              :disabled="!provider.is_active || testing"
            >
              测试
            </button>
            <button class="ghost-action" @click="handleToggleStatus(provider)">
              {{ provider.is_active ? '停用' : '启用' }}
            </button>
            <button class="ghost-action" @click="handleEdit(provider)">编辑</button>
            <button class="ghost-action danger" @click="handleDelete(provider)">删除</button>
          </div>
        </article>
      </div>
    </loading-container>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import LoadingContainer from '@/components/common/LoadingContainer.vue'

export default {
  name: 'ModelList',
  components: {
    LoadingContainer
  },
  data() {
    return {
      filters: {
        search: '',
        provider_type: '',
        is_active: ''
      },
      testing: false
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

    handleFilter() {
      this.loadProviders()
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
      this.testing = true
      try {
        const result = await this.testProviderConnection({
          id: provider.id,
          testPrompt: 'Hello, this is a test.'
        })

        if (result.success) {
          alert(`测试成功! 延迟: ${result.latency_ms}ms`)
        } else {
          alert(`测试失败: ${result.error}`)
        }
      } catch (error) {
        console.error('测试连接失败:', error)
        alert('测试连接失败')
      } finally {
        this.testing = false
      }
    },

    async handleDelete(provider) {
      if (!confirm(`确定要删除模型 "${provider.name}" 吗?`)) {
        return
      }

      try {
        await this.deleteProvider(provider.id)
        alert('删除成功')
      } catch (error) {
        console.error('删除模型失败:', error)
        alert(error.response?.data?.error || '删除失败,该模型可能正在被项目使用')
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
        text2image: 'badge-secondary',
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
  font-size: 2.1rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.primary-action {
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
  font-weight: 500;
  transition: all 0.2s ease;
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
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
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 220px;
}

.search-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  width: 1.25rem;
  height: 1.25rem;
  color: #94a3b8;
}

.search-input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 3rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  outline: none;
}

.search-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.select-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.select-input {
  min-width: 140px;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .card-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (min-width: 1536px) {
  .card-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

.data-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  padding: 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
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

.card-subtitle {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
  word-break: break-all;
  overflow-wrap: anywhere;
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

.usage-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.2rem;
  font-size: 0.8rem;
  text-align: right;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.ghost-action {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.8rem;
}

.ghost-action:hover {
  border-color: rgba(15, 23, 42, 0.1);
}

.ghost-action.danger {
  color: #dc2626;
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

.empty-hint {
  color: #94a3b8;
  margin: 0.6rem 0 1.6rem;
}

.secondary-action {
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  border: none;
}

.muted {
  color: #94a3b8;
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .primary-action {
    width: 100%;
  }
}
</style>
