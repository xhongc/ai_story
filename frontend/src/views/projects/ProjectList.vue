<template>
  <div class="page-shell project-episode-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">
          分集列表
        </h1>
        <p class="page-subtitle">
          {{ pagination.total }} 个分集
        </p>
      </div>
      <button
        class="primary-action"
        @click="goSeriesList"
      >
        <span>返回作品管理</span>
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
          placeholder="搜索分集..."
          class="search-input"
          @keyup.enter="handleFilter"
        >
      </div>

      <div class="status-filters">
        <button
          v-for="status in statusOptions"
          :key="status.value"
          :class="['status-filter-btn', { active: filters.status === status.value }]"
          @click="handleStatusFilter(status.value)"
        >
          {{ status.label }}
        </button>
      </div>
    </div>

    <LoadingContainer :loading="loading">
      <div
        v-if="!loading && projects.length === 0"
        class="empty-state"
      >
        <div class="empty-hero">
          暂无分集
        </div>
        <p class="empty-hint">
          请先在作品管理里创建作品，然后在作品下创建分集。
        </p>
        <button
          class="secondary-action"
          @click="goSeriesList"
        >
          去作品管理
        </button>
      </div>

      <div
        v-else
        class="card-grid"
      >
        <article
          v-for="project in projects"
          :key="project.id"
          class="data-card"
          role="button"
          tabindex="0"
          @click="handleView(project.id)"
          @keyup.enter="handleView(project.id)"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                {{ project.display_name || project.name }}
                <span class="pill">第{{ project.episode_number || '-' }}集</span>
              </h2>
              <p class="card-desc">
                {{ project.series_name || '未归属作品' }}
              </p>
            </div>
            <span class="status-pill">{{ project.status_display }}</span>
          </div>

          <div class="card-meta">
            <div class="meta-item">
              <span class="meta-label">阶段进度</span>
              <span class="meta-value">{{ project.completed_stages_count }}/{{ project.stages_count }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">创建时间</span>
              <span class="meta-value">{{ formatDate(project.created_at) }}</span>
            </div>
          </div>

          <div class="card-footer">
            <span class="meta-time">更新于 {{ formatDate(project.updated_at) }}</span>
            <div class="project-card-actions">
              <button
                class="project-card-action"
                @click.stop="handleEdit(project.id)"
              >
                编辑
              </button>
              <button
                class="project-card-action project-card-action--danger"
                :disabled="deletingProjectId === project.id"
                @click.stop="handleDelete(project)"
              >
                {{ deletingProjectId === project.id ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </LoadingContainer>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

const PROJECT_LIST_FILTER_STORAGE_KEY = 'project_list_filters';

const getSavedProjectFilters = () => {
  const defaultFilters = {
    search: '',
    status: '',
  };

  try {
    const saved = localStorage.getItem(PROJECT_LIST_FILTER_STORAGE_KEY);
    if (!saved) {
      return defaultFilters;
    }

    const parsed = JSON.parse(saved);
    return {
      search: typeof parsed.search === 'string' ? parsed.search : '',
      status: typeof parsed.status === 'string' ? parsed.status : '',
    };
  } catch (error) {
    return defaultFilters;
  }
};

export default {
  name: 'ProjectList',
  components: { LoadingContainer },
  data() {
    const savedFilters = getSavedProjectFilters();

    return {
      loading: false,
      deletingProjectId: null,
      filters: savedFilters,
      statusOptions: [
        { value: '', label: '全部' },
        { value: 'draft', label: '草稿' },
        { value: 'processing', label: '处理中' },
        { value: 'completed', label: '已完成' },
        { value: 'failed', label: '失败' },
        { value: 'paused', label: '已暂停' },
      ],
    };
  },
  computed: {
    ...mapState('projects', ['projects', 'pagination']),
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('projects', ['fetchProjects', 'deleteProject']),
    formatDate,
    persistFilters() {
      try {
        localStorage.setItem(PROJECT_LIST_FILTER_STORAGE_KEY, JSON.stringify(this.filters));
      } catch (error) {
        console.error('保存分集筛选条件失败:', error);
      }
    },
    async fetchData(page = this.pagination.page) {
      this.loading = true;
      try {
        await this.fetchProjects({
          page,
          page_size: this.pagination.pageSize,
          search: this.filters.search,
          status: this.filters.status,
        });
      } finally {
        this.loading = false;
      }
    },
    handleFilter() {
      this.persistFilters();
      this.fetchData(1);
    },
    handleStatusFilter(status) {
      this.filters.status = status;
      this.handleFilter();
    },
    handleView(id) {
      this.$router.push({ name: 'ProjectDetail', params: { id } });
    },
    handleEdit(id) {
      this.$router.push({ name: 'ProjectEdit', params: { id } });
    },
    async handleDelete(project) {
      const displayName = project.display_name || project.name || `第${project.episode_number || '-'}集`;
      const confirmed = await this.$confirm(
        `确定删除分集「${displayName}」吗？此操作不可恢复。`,
        '删除分集',
        { tone: 'danger', confirmText: '删除' }
      );
      if (!confirmed) {
        return;
      }

      this.deletingProjectId = project.id;
      try {
        await this.deleteProject(project.id);
        this.$message.success('分集已删除');
      } catch (error) {
        console.error('Failed to delete project:', error);
        this.$message.error('删除分集失败');
      } finally {
        this.deletingProjectId = null;
      }
    },
    goSeriesList() {
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

.primary-action {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
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

.filter-card {
  display: flex;
  gap: 1rem;
  margin-bottom: 2.5rem;
  flex-wrap: wrap;
  padding: 1rem 1.25rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
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
  max-width: 420px;
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
  padding: 0.875rem 1rem 0.875rem 3rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.9);
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

.layout-shell.theme-dark .status-filter-btn {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #cbd5e1;
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

.layout-shell.theme-dark .status-filter-btn.active {
  background: rgba(94, 234, 212, 0.2);
  color: #e2e8f0;
  border-color: rgba(94, 234, 212, 0.5);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.data-card {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%)
      0 0 / 0 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.layout-shell.theme-dark .data-card {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%)
      0 0 / 0 3px no-repeat,
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

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin: 0;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-desc {
  margin: 0.5rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.pill,
.status-pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
}

.pill {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
}

.status-pill {
  background: rgba(148, 163, 184, 0.14);
  color: #334155;
}

.layout-shell.theme-dark .pill {
  background: rgba(94, 234, 212, 0.22);
  color: #e2e8f0;
}

.layout-shell.theme-dark .status-pill {
  background: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.card-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.75rem 1rem;
}

.layout-shell.theme-dark .card-meta {
  background: rgba(30, 41, 59, 0.6);
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

.layout-shell.theme-dark .meta-value {
  color: #e2e8f0;
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

.project-card-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.data-card:hover .project-card-actions {
  opacity: 1;
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

.secondary-action {
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  background: #0f172a;
  color: #ffffff;
  border: none;
}

.layout-shell.theme-dark .secondary-action {
  background: #e2e8f0;
  color: #0f172a;
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
    flex-wrap: wrap;
  }
}
</style>
