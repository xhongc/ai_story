<template>
  <div class="page-shell asset-list">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">资产管理</h1>
        <p class="page-subtitle">管理全局变量与系统资源</p>
      </div>
      <button class="primary-action" @click="handleCreate">新建资产</button>
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
        <div class="empty-hero">暂无资产</div>
        <p class="empty-hint">创建第一个资产，统一管理变量与资源</p>
        <button class="secondary-action" @click="handleCreate">新建资产</button>
      </div>

      <div v-else class="card-grid">
        <article v-for="asset in assets" :key="asset.id" class="data-card">
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
                @click="previewImage(asset.image_url)"
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
                @click="handleEdit(asset)"
                title="编辑"
              >
                编辑
              </button>
              <button
                class="ghost-action danger"
                @click="handleDelete(asset)"
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
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-width: 0;
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

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(148, 163, 184, 0.16);
  color: #0f172a;
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

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.asset-key {
  font-family: 'Courier New', monospace;
  background: rgba(148, 163, 184, 0.15);
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  font-size: 0.85rem;
  max-width: 100%;
  overflow-wrap: anywhere;
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
}

.row-actions {
  display: flex;
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

.muted {
  color: #94a3b8;
  font-size: 0.85rem;
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

  .row-actions {
    flex-direction: column;
  }
}
</style>
