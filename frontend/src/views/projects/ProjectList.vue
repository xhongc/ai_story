<template>
  <div class="page-shell project-list">
    <!-- 顶部工具栏 -->
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">项目管理</h1>
        <p class="page-subtitle">{{ pagination.total }} 个项目</p>
      </div>
      <button class="primary-action" @click="handleCreate">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        <span>新建项目</span>
      </button>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-card">
      <div class="search-box">
        <svg class="search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          v-model="filters.search"
          type="text"
          placeholder="搜索项目..."
          class="search-input"
          @keyup.enter="handleFilter"
        />
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

    <!-- 项目瀑布流 -->
    <loading-container :loading="loading">
      <div v-if="projects.length > 0" class="masonry-grid">
        <div
          v-for="project in projects"
          :key="project.id"
          class="project-card"
          @click="handleView(project.id)"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <div class="card-status">
              <span :class="['status-dot', getStatusClass(project.status)]"></span>
              <span class="status-text">{{ getStatusLabel(project.status) }}</span>
            </div>
            <div class="card-actions" @click.stop>
              <button class="action-btn" @click="handleDelete(project)">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 卡片内容 -->
          <div class="card-content">
            <h3 class="card-title">{{ project.name }}</h3>
            <p v-if="project.description" class="card-description">
              {{ project.description }}
            </p>
          </div>

          <!-- 卡片底部 -->
          <div class="card-footer">
            <div class="card-meta">
              <svg class="meta-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span class="meta-text">{{ formatDate(project.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <svg class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p class="empty-text">还没有项目</p>
        <p class="empty-hint">创建你的第一个 AI 故事项目</p>
        <button class="secondary-action" @click="handleCreate">
          开始创作
        </button>
      </div>

      <!-- 分页 -->
      <div v-if="projects.length > 0" class="pagination">
        <button
          class="pagination-btn"
          :disabled="pagination.page === 1"
          @click="handlePageChange(pagination.page - 1)"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span class="pagination-info">{{ pagination.page }} / {{ totalPages }}</span>
        <button
          class="pagination-btn"
          :disabled="pagination.page >= totalPages"
          @click="handlePageChange(pagination.page + 1)"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </loading-container>

    <!-- 删除确认模态框 -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box-modern">
        <h3 class="modal-title">删除项目</h3>
        <p class="modal-text">
          确定要删除 <span class="font-semibold">"{{ deletingProject?.name }}"</span> 吗？此操作无法撤销。
        </p>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closeDeleteModal">取消</button>
          <button class="btn-delete" @click="confirmDelete">删除</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeDeleteModal">close</button>
      </form>
    </dialog>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'ProjectList',
  components: {
    LoadingContainer,
  },
  data() {
    return {
      loading: false,
      filters: {
        search: '',
        status: '',
      },
      deletingProject: null,
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
    totalPages() {
      return Math.ceil(this.pagination.total / this.pagination.pageSize);
    },
  },
  created() {
    this.fetchData();
  },
  methods: {
    ...mapActions('projects', ['fetchProjects', 'deleteProject']),
    formatDate,

    async fetchData() {
      this.loading = true;
      try {
        await this.fetchProjects({
          page: this.pagination.page,
          page_size: this.pagination.pageSize,
          search: this.filters.search,
          status: this.filters.status,
        });
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      } finally {
        this.loading = false;
      }
    },

    handleFilter() {
      this.pagination.page = 1;
      this.fetchData();
    },

    handleStatusFilter(status) {
      this.filters.status = status;
      this.handleFilter();
    },

    handlePageChange(page) {
      if (page < 1 || page > this.totalPages) return;
      this.pagination.page = page;
      this.fetchData();
    },

    handleCreate() {
      this.$router.push('/projects/create');
    },

    handleView(id) {
      this.$router.push(`/projects/${id}`);
    },

    handleDelete(project) {
      this.deletingProject = project;
      this.$refs.deleteModal.showModal();
    },

    closeDeleteModal() {
      this.$refs.deleteModal.close();
      this.deletingProject = null;
    },

    async confirmDelete() {
      if (!this.deletingProject) return;

      try {
        await this.deleteProject(this.deletingProject.id);
        this.closeDeleteModal();
        this.fetchData();
      } catch (error) {
        console.error('Failed to delete project:', error);
      }
    },

    getStatusClass(status) {
      const statusMap = {
        draft: 'status-draft',
        processing: 'status-processing',
        completed: 'status-completed',
        failed: 'status-failed',
        paused: 'status-paused',
      };
      return statusMap[status] || 'status-draft';
    },

    getStatusLabel(status) {
      const labelMap = {
        draft: '草稿',
        processing: '处理中',
        completed: '已完成',
        failed: '失败',
        paused: '已暂停',
      };
      return labelMap[status] || status;
    },
  },
};
</script>

<style scoped>
/* 现代极简风格 - 项目列表 */

.page-shell {
  min-height: 100%;
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
  flex: 1;
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
  background: #ffffff;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-action:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.primary-action:active {
  transform: translateY(0);
}

/* 筛选区域 */
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
  padding: 0.875rem 1rem 0.875rem 3rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  font-size: 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.2s ease;
  outline: none;
}

.search-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.search-input::placeholder {
  color: #cbd5e1;
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

/* 瀑布流网格 */
.masonry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

/* 项目卡片 */
.project-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.project-card::before {
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

.project-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  border-color: rgba(148, 163, 184, 0.35);
}

.project-card:hover::before {
  transform: scaleX(1);
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-dot.status-draft {
  background: #94a3b8;
}

.status-dot.status-processing {
  background: #3b82f6;
}

.status-dot.status-completed {
  background: #10b981;
}

.status-dot.status-failed {
  background: #ef4444;
}

.status-dot.status-paused {
  background: #f59e0b;
}

.status-text {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.project-card:hover .card-actions {
  opacity: 1;
}

.action-btn {
  padding: 0.5rem;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(248, 113, 113, 0.12);
  color: #dc2626;
}

/* 卡片内容 */
.card-content {
  margin-bottom: 1.25rem;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 0.75rem 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-description {
  font-size: 0.875rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 卡片底部 */
.card-footer {
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.meta-icon {
  width: 1rem;
  height: 1rem;
  color: #cbd5e1;
}

.meta-text {
  font-size: 0.8rem;
  color: #94a3b8;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem 2rem;
  text-align: center;
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  color: #cbd5e1;
  margin-bottom: 1.5rem;
}

.empty-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 0.5rem 0;
}

.empty-hint {
  font-size: 0.95rem;
  color: #94a3b8;
  margin: 0 0 2rem 0;
}

.secondary-action {
  padding: 0.875rem 2rem;
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: 999px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.secondary-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 3rem;
}

.pagination-btn {
  padding: 0.625rem;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 10px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  min-width: 80px;
  text-align: center;
}

/* 模态框 */
.modal-box-modern {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  padding: 2rem;
  max-width: 400px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 1rem 0;
}

.modal-text {
  font-size: 0.95rem;
  color: #64748b;
  line-height: 1.6;
  margin: 0 0 2rem 0;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 0.75rem 1.5rem;
  background: #f8fafc;
  color: #64748b;
  border: none;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel:hover {
  background: #f1f5f9;
}

.btn-delete {
  padding: 0.75rem 1.5rem;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-delete:hover {
  background: #dc2626;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-title {
    font-size: 2rem;
  }

  .page-header {
    flex-direction: column;
    gap: 1.5rem;
  }

  .primary-action {
    width: 100%;
    justify-content: center;
  }

  .filter-card {
    flex-direction: column;
  }

  .search-box {
    max-width: 100%;
  }

  .masonry-grid {
    grid-template-columns: 1fr;
  }
}
</style>
