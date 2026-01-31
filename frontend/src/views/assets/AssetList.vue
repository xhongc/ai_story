<template>
  <div class="asset-list">
    <!-- 页面头部 -->
    <PageCard title="资产管理">
      <template slot="header-right">
        <button class="btn btn-primary btn-sm" @click="handleCreate">
          + 新建资产
        </button>
      </template>

      <!-- 搜索和过滤 -->
      <div class="mb-6 flex gap-4 flex-wrap">
        <div class="form-control flex-1 min-w-[200px]">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索资产键或描述..."
            class="input input-bordered w-full"
            @input="handleSearch"
          />
        </div>
        <div class="form-control">
          <select v-model="filterScope" class="select select-bordered" @change="handleFilter">
            <option value="">全部作用域</option>
            <option value="user">用户级</option>
            <option value="system">系统级</option>
          </select>
        </div>
        <div class="form-control">
          <select v-model="filterType" class="select select-bordered" @change="handleFilter">
            <option value="">全部类型</option>
            <option value="string">字符串</option>
            <option value="number">数字</option>
            <option value="boolean">布尔值</option>
            <option value="json">JSON对象</option>
            <option value="image">图片</option>
          </select>
        </div>
        <div class="form-control">
          <select v-model="filterGroup" class="select select-bordered" @change="handleFilter">
            <option value="">全部分组</option>
            <option v-for="group in groups" :key="group" :value="group">
              {{ group }}
            </option>
          </select>
        </div>
      </div>

      <!-- Loading状态 -->
      <LoadingContainer :loading="loading">
        <!-- 空状态 -->
        <div v-if="!loading && assets.length === 0" class="text-center py-12">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-16 w-16 mx-auto text-base-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
            />
          </svg>
          <p class="mt-4 text-base-content/60">暂无资产</p>
          <button class="btn btn-primary btn-sm mt-4" @click="handleCreate">创建第一个资产</button>
        </div>

        <!-- 资产表格 -->
        <div v-else class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>资产键</th>
                <th>值/预览</th>
                <th>类型</th>
                <th>作用域</th>
                <th>分组</th>
                <th>描述</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="asset in assets" :key="asset.id">
                <td>
                  <code class="text-sm bg-base-200 px-2 py-1 rounded">{{ asset.key }}</code>
                </td>
                <td>
                  <!-- 图片类型显示缩略图 -->
                  <div v-if="asset.variable_type === 'image'" class="flex items-center">
                    <img
                      v-if="asset.image_url"
                      :src="asset.image_url"
                      :alt="asset.key"
                      class="w-12 h-12 object-cover rounded cursor-pointer hover:opacity-80"
                      @click="previewImage(asset.image_url)"
                    />
                    <span v-else class="text-base-content/40">未上传</span>
                  </div>
                  <!-- 其他类型显示值 -->
                  <div v-else class="max-w-xs truncate" :title="String(asset.value)">
                    {{ formatValue(asset) }}
                  </div>
                </td>
                <td>
                  <span class="badge badge-sm" :class="getTypeBadgeClass(asset.variable_type)">
                    {{ asset.variable_type_display }}
                  </span>
                </td>
                <td>
                  <span class="badge badge-sm" :class="getScopeBadgeClass(asset.scope)">
                    {{ asset.scope_display }}
                  </span>
                </td>
                <td>
                  <span v-if="asset.group" class="badge badge-outline badge-sm">
                    {{ asset.group }}
                  </span>
                  <span v-else class="text-base-content/40">-</span>
                </td>
                <td>
                  <div class="max-w-xs truncate" :title="asset.description">
                    {{ asset.description || '-' }}
                  </div>
                </td>
                <td>
                  <StatusBadge :status="asset.is_active ? 'active' : 'inactive'" />
                </td>
                <td class="text-sm text-base-content/60">
                  {{ formatDate(asset.updated_at) }}
                </td>
                <td>
                  <div class="flex gap-2">
                    <button
                      class="btn btn-ghost btn-xs"
                      @click="handleEdit(asset)"
                      title="编辑"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                        />
                      </svg>
                    </button>
                    <button
                      class="btn btn-ghost btn-xs text-error"
                      @click="handleDelete(asset)"
                      :disabled="asset.scope === 'system' && !isAdmin"
                      title="删除"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                          clip-rule="evenodd"
                        />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </LoadingContainer>
    </PageCard>

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
import PageCard from '@/components/common/PageCard.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';

export default {
  name: 'AssetList',
  components: {
    PageCard,
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
.asset-list {
  padding: 1.5rem;
}

code {
  font-family: 'Courier New', monospace;
}
</style>
