<template>
  <div class="page-shell prompt-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">提示词管理</h1>
        <p class="page-subtitle">{{ total }} 个提示词集</p>
      </div>
      <button class="primary-action" @click="handleCreate">
        <span>创建提示词集</span>
      </button>
    </div>

    <div class="filter-card">
      <div class="search-box">
        <svg class="search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索提示词集..."
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="status-filters">
        <button
          v-for="status in statusOptions"
          :key="status.value"
          :class="['status-filter-btn', { active: filterStatus === status.value }]"
          @click="handleStatusFilter(status.value)"
        >
          {{ status.label }}
        </button>
      </div>
      <div class="status-filters">
        <button
          v-for="option in defaultOptions"
          :key="option.value"
          :class="['status-filter-btn', { active: filterDefault === option.value }]"
          @click="handleDefaultFilter(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <LoadingContainer :loading="loading">
      <div v-if="!loading && promptSets.length === 0" class="empty-state">
        <div class="empty-hero">暂无提示词集</div>
        <p class="empty-hint">创建第一个提示词集，快速复用你的最佳实践</p>
        <button class="secondary-action" @click="handleCreate">创建提示词集</button>
      </div>

      <div v-else class="card-grid">
        <article
          v-for="set in promptSets"
          :key="set.id"
          class="data-card"
          role="button"
          tabindex="0"
          @click="handleView(set)"
          @keyup.enter="handleView(set)"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                {{ set.name }}
                <span v-if="set.is_default" class="pill pill-primary">默认</span>
              </h2>
              <p class="card-desc">{{ set.description || '暂无描述' }}</p>
            </div>
            <StatusBadge :status="set.is_active ? 'active' : 'inactive'" />
          </div>

          <div class="card-meta">
            <div class="meta-item">
              <span class="meta-label">模板</span>
              <span class="meta-value">{{ set.templates_count || 0 }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建人</span>
              <span class="meta-value">{{ set.created_by?.username || '未知' }}</span>
            </div>
          </div>

          <div class="card-footer">
            <span class="meta-time">更新于 {{ formatDate(set.updated_at) }}</span>
            <div class="card-actions" @click.stop>
              <div class="dropdown dropdown-end">
                <label tabindex="0" class="ghost-action" @click.stop>更多</label>
                <ul
                  tabindex="0"
                  class="dropdown-content z-[1] menu p-2 shadow-lg bg-base-100 rounded-box w-52 border border-base-300"
                >
                  <li v-if="!set.is_default"><a @click="handleSetDefault(set)">设为默认</a></li>
                  <li><a @click="handleClone(set)">克隆</a></li>
                  <li><a @click="handleEdit(set)">编辑描述</a></li>
                  <li><a @click="handleToggleActive(set)">{{ set.is_active ? '停用' : '启用' }}</a></li>
                  <li class="text-error"><a @click="handleDelete(set)">删除</a></li>
                </ul>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div v-if="total > pageSize" class="pagination">
        <button
          class="pagination-btn"
          :disabled="currentPage === 1"
          @click="handlePageChange(currentPage - 1)"
        >
          «
        </button>
        <span class="pagination-info">第 {{ currentPage }} 页</span>
        <button
          class="pagination-btn"
          :disabled="currentPage * pageSize >= total"
          @click="handlePageChange(currentPage + 1)"
        >
          »
        </button>
      </div>
    </LoadingContainer>

    <!-- 克隆对话框 -->
    <dialog ref="cloneDialog" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">克隆提示词集</h3>
        <p class="py-4">请为新的提示词集输入名称：</p>
        <div class="form-control">
          <input
            v-model="cloneName"
            type="text"
            placeholder="新提示词集名称"
            class="input input-bordered w-full"
          />
        </div>
        <div class="modal-action">
          <button class="btn" @click="$refs.cloneDialog.close()">取消</button>
          <button class="btn btn-primary" @click="confirmClone" :disabled="!cloneName">
            确认克隆
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>关闭</button>
      </form>
    </dialog>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import StatusBadge from '@/components/common/StatusBadge.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'PromptList',
  components: {
    StatusBadge,
    LoadingContainer,
  },
  data() {
    return {
      searchKeyword: '',
      filterStatus: '',
      filterDefault: '',
      currentPage: 1,
      pageSize: 9,
      cloneName: '',
      cloneTarget: null,
      searchTimer: null,
      statusOptions: [
        { value: '', label: '全部' },
        { value: 'active', label: '已启用' },
        { value: 'inactive', label: '已停用' },
      ],
      defaultOptions: [
        { value: '', label: '全部' },
        { value: 'true', label: '默认' },
        { value: 'false', label: '非默认' },
      ],
    };
  },
  computed: {
    ...mapState('prompts', {
      promptSets: (state) => state.promptSets,
      total: (state) => state.promptSetsTotal,
      loading: (state) => state.promptSetsLoading,
    }),
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('prompts', [
      'fetchPromptSets',
      'deletePromptSet',
      'clonePromptSet',
      'setDefaultPromptSet',
      'updatePromptSet',
    ]),
    formatDate,

    async fetchData() {
      const params = {
        page: this.currentPage,
        page_size: this.pageSize,
      };

      if (this.searchKeyword) {
        params.search = this.searchKeyword;
      }

      if (this.filterStatus === 'active') {
        params.is_active = true;
      } else if (this.filterStatus === 'inactive') {
        params.is_active = false;
      }

      if (this.filterDefault === 'true') {
        params.is_default = true;
      } else if (this.filterDefault === 'false') {
        params.is_default = false;
      }

      try {
        await this.fetchPromptSets(params);
      } catch (error) {
        console.error('获取提示词集列表失败:', error);
      }
    },

    handleSearch() {
      // 防抖处理
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.currentPage = 1;
        this.fetchData();
      }, 500);
    },

    handleFilter() {
      this.currentPage = 1;
      this.fetchData();
    },

    handleStatusFilter(status) {
      this.filterStatus = status;
      this.handleFilter();
    },

    handleDefaultFilter(value) {
      this.filterDefault = value;
      this.handleFilter();
    },

    handlePageChange(page) {
      this.currentPage = page;
      this.fetchData();
    },

    handleCreate() {
      this.$router.push('/prompts/sets/create');
    },

    handleView(set) {
      this.$router.push(`/prompts/sets/${set.id}/edit`);
    },

    handleEdit(set) {
      this.$router.push(`/prompts/sets/${set.id}/edit`);
    },

    handleClone(set) {
      this.cloneTarget = set;
      this.cloneName = `${set.name} (副本)`;
      this.$refs.cloneDialog.showModal();
    },

    async confirmClone() {
      if (!this.cloneName || !this.cloneTarget) return;

      try {
        await this.clonePromptSet({
          id: this.cloneTarget.id,
          name: this.cloneName,
        });
        this.$refs.cloneDialog.close();
        this.cloneName = '';
        this.cloneTarget = null;
        // 刷新列表
        await this.fetchData();
      } catch (error) {
        console.error('克隆提示词集失败:', error);
      }
    },

    async handleSetDefault(set) {
      try {
        await this.setDefaultPromptSet(set.id);
        await this.fetchData();
      } catch (error) {
        console.error('设置默认提示词集失败:', error);
      }
    },

    async handleToggleActive(set) {
      try {
        await this.updatePromptSet({
          id: set.id,
          data: { is_active: !set.is_active },
        });
        await this.fetchData();
      } catch (error) {
        console.error('更新提示词集状态失败:', error);
      }
    },

    async handleDelete(set) {
      if (!confirm(`确定要删除提示词集 "${set.name}" 吗？此操作不可恢复。`)) {
        return;
      }

      try {
        await this.deletePromptSet(set.id);
        await this.fetchData();
      } catch (error) {
        console.error('删除提示词集失败:', error);
      }
    },
  },
};
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: 2.5rem 3.5rem 3rem;
  background: transparent;
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
  min-width: 240px;
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

.status-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-filter-btn {
  padding: 0.625rem 1.25rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #64748b;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-filter-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.status-filter-btn.active {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  border-color: rgba(20, 184, 166, 0.5);
}


.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.data-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 0;
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

.data-card:hover::before {
  transform: scaleX(1);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0;
}

.card-desc {
  margin: 0.5rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
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
}

.meta-time {
  font-size: 0.8rem;
  color: #94a3b8;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.data-card:hover .card-actions {
  opacity: 1;
}

.ghost-action {
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.85rem;
}

.ghost-action:hover {
  border-color: rgba(15, 23, 42, 0.1);
  background: rgba(15, 23, 42, 0.08);
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

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2.5rem;
}

.pagination-btn {
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
}

.pagination-info {
  font-size: 0.9rem;
  color: #64748b;
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

  .card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .card-actions {
    opacity: 1;
  }
}
</style>
