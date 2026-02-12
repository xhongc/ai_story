<template>
  <div class="page-shell asset-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">资产管理</h1>
        <p class="page-subtitle">管理全局变量与系统资源</p>
      </div>
      <button class="primary-action" @click="handleCreate">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        <span>新建资产</span>
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
          placeholder="搜索资产键或描述..."
          class="search-input"
          @input="handleSearch"
        />
      </div>
      <div class="select-group">
        <select v-model="filterScope" class="select-input" @change="handleFilter">
          <option value="">全部作用域</option>
          <option value="user">用户级</option>
          <option value="system">系统级</option>
        </select>
        <select v-model="filterType" class="select-input" @change="handleFilter">
          <option value="">全部类型</option>
          <option value="string">字符串</option>
          <option value="number">数字</option>
          <option value="boolean">布尔值</option>
          <option value="json">JSON对象</option>
          <option value="image">图片</option>
        </select>
        <select v-model="filterGroup" class="select-input" @change="handleFilter">
          <option value="">全部分组</option>
          <option v-for="group in groups" :key="group" :value="group">
            {{ group }}
          </option>
        </select>
      </div>
    </div>

    <LoadingContainer :loading="loading" class="loading-container">
      <div v-if="!loading && assets.length === 0" class="empty-state">
        <svg class="empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p class="empty-text">暂无资产</p>
        <p class="empty-hint">创建第一个资产，统一管理变量与资源</p>
        <button class="secondary-action" @click="handleCreate">新建资产</button>
      </div>

      <div v-else class="card-grid">
        <article
          v-for="asset in assets"
          :key="asset.id"
          class="data-card"
          @click="handleEdit(asset)"
          role="button"
          tabindex="0"
          @keydown.enter="handleEdit(asset)"
          @keydown.space.prevent="handleEdit(asset)"
        >
          <div class="card-header">
            <code class="asset-key">{{ asset.key }}</code>
            <StatusBadge :status="asset.is_active ? 'active' : 'inactive'" />
          </div>

          <div class="card-value">
            <div v-if="asset.variable_type === 'image'" class="thumb-cell">
              <img
                v-if="asset.image_url"
                :src="asset.image_url"
                :alt="asset.key"
                class="thumb"
                @click.stop="previewImage(asset.image_url)"
              />
              <span v-else class="muted">未上传</span>
            </div>
            <div v-else class="value-text" :title="String(asset.value)">
              {{ formatValue(asset) }}
            </div>
          </div>

          <div class="card-tags">
            <span class="badge badge-sm" :class="getTypeBadgeClass(asset.variable_type)">
              {{ asset.variable_type_display }}
            </span>
            <span class="badge badge-sm" :class="getScopeBadgeClass(asset.scope)">
              {{ asset.scope_display }}
            </span>
            <span v-if="asset.group" class="pill">{{ asset.group }}</span>
          </div>

          <p class="card-desc">
            {{ asset.description || '暂无描述' }}
          </p>

          <div class="card-meta">
            <span class="muted">更新于 {{ formatDate(asset.updated_at) }}</span>
            <div class="row-actions">
              <button
                class="ghost-action"
                @click.stop="handleDelete(asset)"
                :disabled="asset.scope === 'system' && !isAdmin"
                title="删除"
              >
                删除
              </button>
            </div>
          </div>
        </article>
      </div>
    </LoadingContainer>

    <!-- 图片预览弹窗 -->
    <div v-if="previewImageUrl" class="modal modal-open" @click="previewImageUrl = null">
      <div class="modal-box max-w-4xl" @click.stop>
        <img :src="previewImageUrl" alt="预览" class="w-full" />
        <div class="modal-action">
          <button class="btn" @click="previewImageUrl = null">关闭</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="previewImageUrl = null"></div>
    </div>
  </div>
</template>

<script>
import { globalVariableAPI } from '@/api/prompts';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';

export default {
  name: 'AssetList',
  components: {
    LoadingContainer,
    StatusBadge,
  },
  data() {
    return {
      loading: false,
      assets: [],
      groups: [],
      searchKeyword: '',
      filterScope: '',
      filterType: '',
      filterGroup: '',
      previewImageUrl: null,
    };
  },
  computed: {
    isAdmin() {
      return this.$store.getters['auth/isAdmin'];
    },
  },
  created() {
    this.loadAssets();
    this.loadGroups();
  },
  methods: {
    async loadAssets() {
      this.loading = true;
      try {
        const params = {
          search: this.searchKeyword || undefined,
          scope: this.filterScope || undefined,
          variable_type: this.filterType || undefined,
          group: this.filterGroup || undefined,
        };
        const response = await globalVariableAPI.getList(params);
        this.assets = response.results || [];
      } catch (error) {
        console.error('加载资产失败:', error);
      } finally {
        this.loading = false;
      }
    },

    async loadGroups() {
      try {
        const response = await globalVariableAPI.getGroups();
        this.groups = response.groups || [];
      } catch (error) {
        console.error('加载分组失败:', error);
      }
    },

    handleSearch() {
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.loadAssets();
      }, 500);
    },

    handleFilter() {
      this.loadAssets();
    },

    handleCreate() {
      this.$router.push({ name: 'AssetCreate' });
    },

    handleEdit(asset) {
      this.$router.push({ name: 'AssetDetail', params: { id: asset.id } });
    },

    async handleDelete(asset) {
      if (asset.scope === 'system' && !this.isAdmin) {
        return;
      }

      const confirmed = await this.$confirm(
        `确定要删除资产 "${asset.key}" 吗？`,
        '删除确认'
      );

      if (!confirmed) return;

      try {
        await globalVariableAPI.delete(asset.id);
        this.loadAssets();
        this.loadGroups();
      } catch (error) {
        console.error('删除失败:', error);
      }
    },

    previewImage(url) {
      this.previewImageUrl = url;
    },

    formatValue(asset) {
      const value = asset.value;
      if (asset.variable_type === 'json') {
        try {
          return JSON.stringify(JSON.parse(value), null, 2);
        } catch {
          return value;
        }
      }
      if (value && value.length > 50) {
        return value.substring(0, 50) + '...';
      }
      return value || '-';
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    },

    getTypeBadgeClass(type) {
      const classes = {
        string: 'badge-info',
        number: 'badge-success',
        boolean: 'badge-warning',
        json: 'badge-secondary',
        image: 'badge-accent',
      };
      return classes[type] || 'badge-ghost';
    },

    getScopeBadgeClass(scope) {
      return scope === 'system' ? 'badge-error' : 'badge-primary';
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

.select-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

.select-input {
  min-width: 140px;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .select-input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #e2e8f0;
}

.select-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
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
  gap: 0.9rem;
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

.data-card:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
  border-color: rgba(20, 184, 166, 0.6);
}

.data-card:hover::before {
  transform: scaleX(1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.card-value {
  min-height: 48px;
}

.value-text {
  color: #0f172a;
  font-size: 0.9rem;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.layout-shell.theme-dark .value-text {
  color: #e2e8f0;
}

.card-tags {
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
  background: rgba(59, 130, 246, 0.16);
  border-color: rgba(59, 130, 246, 0.3);
  color: #1d4ed8;
}

.layout-shell.theme-dark .badge-info {
  color: #93c5fd;
}

.badge-success {
  background: rgba(16, 185, 129, 0.16);
  border-color: rgba(16, 185, 129, 0.3);
  color: #047857;
}

.layout-shell.theme-dark .badge-success {
  color: #6ee7b7;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.18);
  border-color: rgba(245, 158, 11, 0.35);
  color: #b45309;
}

.layout-shell.theme-dark .badge-warning {
  color: #fcd34d;
}

.badge-secondary {
  background: rgba(148, 163, 184, 0.2);
  border-color: rgba(148, 163, 184, 0.35);
  color: #475569;
}

.layout-shell.theme-dark .badge-secondary {
  color: #e2e8f0;
}

.badge-accent {
  background: rgba(14, 165, 233, 0.16);
  border-color: rgba(14, 165, 233, 0.3);
  color: #0284c7;
}

.layout-shell.theme-dark .badge-accent {
  color: #7dd3fc;
}

.badge-primary {
  background: rgba(20, 184, 166, 0.16);
  border-color: rgba(20, 184, 166, 0.35);
  color: #0f766e;
}

.layout-shell.theme-dark .badge-primary {
  color: #5eead4;
}

.badge-error {
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.3);
  color: #b91c1c;
}

.layout-shell.theme-dark .badge-error {
  color: #fca5a5;
}

.pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(148, 163, 184, 0.16);
  color: #0f172a;
}

.layout-shell.theme-dark .pill {
  background: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.card-desc {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.asset-key {
  font-family: 'Courier New', monospace;
  background: rgba(148, 163, 184, 0.12);
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  font-size: 0.85rem;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.layout-shell.theme-dark .asset-key {
  background: rgba(148, 163, 184, 0.2);
  color: #e2e8f0;
}

.thumb-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.thumb {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  object-fit: cover;
  cursor: pointer;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.layout-shell.theme-dark .thumb {
  border-color: rgba(148, 163, 184, 0.3);
}

.row-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.data-card:hover .row-actions {
  opacity: 1;
}

.ghost-action {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(15, 23, 42, 0.04);
  color: #0f172a;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .ghost-action {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
}

.ghost-action:hover {
  border-color: rgba(248, 113, 113, 0.35);
  background: rgba(248, 113, 113, 0.12);
  color: #dc2626;
}

.layout-shell.theme-dark .ghost-action:hover {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

.ghost-action.danger {
  color: #dc2626;
}

.muted {
  color: #94a3b8;
  font-size: 0.85rem;
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

  .filter-card {
    flex-direction: column;
  }

  .row-actions {
    flex-direction: column;
  }
}
</style>
