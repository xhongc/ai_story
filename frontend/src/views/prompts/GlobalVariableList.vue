<template>
  <div class="global-variable-list">
    <!-- 页面头部 -->
    <PageCard title="全局变量管理">
      <template slot="header-right">
        <button class="btn btn-primary btn-sm" @click="handleCreate">
          + 创建变量
        </button>
      </template>

      <!-- 搜索和过滤 -->
      <div class="mb-6 flex gap-4 flex-wrap">
        <div class="form-control flex-1 min-w-[200px]">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索变量键或描述..."
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
        <div v-if="!loading && variables.length === 0" class="text-center py-12">
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
              d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
            />
          </svg>
          <p class="mt-4 text-base-content/60">暂无全局变量</p>
          <button class="btn btn-primary btn-sm mt-4" @click="handleCreate">创建第一个变量</button>
        </div>

        <!-- 变量表格 -->
        <div v-else class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th>变量键</th>
                <th>值</th>
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
              <tr v-for="variable in variables" :key="variable.id">
                <td>
                  <code class="text-sm bg-base-200 px-2 py-1 rounded">{{ variable.key }}</code>
                </td>
                <td>
                  <div class="max-w-xs truncate" :title="String(variable.value)">
                    {{ formatValue(variable) }}
                  </div>
                </td>
                <td>
                  <span class="badge badge-sm" :class="getTypeBadgeClass(variable.variable_type)">
                    {{ variable.variable_type_display }}
                  </span>
                </td>
                <td>
                  <span class="badge badge-sm" :class="getScopeBadgeClass(variable.scope)">
                    {{ variable.scope_display }}
                  </span>
                </td>
                <td>
                  <span v-if="variable.group" class="badge badge-outline badge-sm">
                    {{ variable.group }}
                  </span>
                  <span v-else class="text-base-content/40">-</span>
                </td>
                <td>
                  <div class="max-w-xs truncate" :title="variable.description">
                    {{ variable.description || '-' }}
                  </div>
                </td>
                <td>
                  <StatusBadge :status="variable.is_active ? 'active' : 'inactive'" />
                </td>
                <td class="text-sm text-base-content/60">
                  {{ formatDate(variable.updated_at) }}
                </td>
                <td>
                  <div class="flex gap-2">
                    <button
                      class="btn btn-ghost btn-xs"
                      @click="handleEdit(variable)"
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
                      @click="handleDelete(variable)"
                      :disabled="variable.scope === 'system' && !isAdmin"
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

    <!-- 创建/编辑对话框 -->
    <VariableFormModal
      v-if="showFormModal"
      :variable="editingVariable"
      :groups="groups"
      @close="showFormModal = false"
      @success="handleFormSuccess"
    />
  </div>
</template>

<script>
import { globalVariableAPI } from '@/api/prompts';
import PageCard from '@/components/common/PageCard.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import VariableFormModal from '@/components/prompts/VariableFormModal.vue';

export default {
  name: 'GlobalVariableList',
  components: {
    PageCard,
    LoadingContainer,
    StatusBadge,
    VariableFormModal,
  },
  data() {
    return {
      loading: false,
      variables: [],
      groups: [],
      searchKeyword: '',
      filterScope: '',
      filterType: '',
      filterGroup: '',
      showFormModal: false,
      editingVariable: null,
    };
  },
  computed: {
    isAdmin() {
      return this.$store.getters['auth/isAdmin'];
    },
  },
  created() {
    this.loadVariables();
    this.loadGroups();
  },
  methods: {
    async loadVariables() {
      this.loading = true;
      try {
        const params = {
          search: this.searchKeyword || undefined,
          scope: this.filterScope || undefined,
          variable_type: this.filterType || undefined,
          group: this.filterGroup || undefined,
        };
        const response = await globalVariableAPI.getList(params);
        console.log(response)
        this.variables = response.results || [];
      } catch (error) {
        console.error('加载变量失败:', error);
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
      // 防抖搜索
      clearTimeout(this.searchTimer);
      this.searchTimer = setTimeout(() => {
        this.loadVariables();
      }, 500);
    },

    handleFilter() {
      this.loadVariables();
    },

    handleCreate() {
      this.editingVariable = null;
      this.showFormModal = true;
    },

    handleEdit(variable) {
      this.editingVariable = variable;
      this.showFormModal = true;
    },

    async handleDelete(variable) {
      if (variable.scope === 'system' && !this.isAdmin) {
        return;
      }

      const confirmed = await this.$confirm(
        `确定要删除变量 "${variable.key}" 吗？`,
        '删除确认'
      );

      if (!confirmed) return;

      try {
        await globalVariableAPI.delete(variable.id);
        this.loadVariables();
        this.loadGroups();
      } catch (error) {
        console.error('删除失败:', error);
      }
    },

    handleFormSuccess() {
      this.showFormModal = false;
      this.loadVariables();
      this.loadGroups();
    },

    formatValue(variable) {
      const value = variable.value;
      if (variable.variable_type === 'json') {
        try {
          return JSON.stringify(JSON.parse(value), null, 2);
        } catch {
          return value;
        }
      }
      if (value.length > 50) {
        return value.substring(0, 50) + '...';
      }
      return value;
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
.global-variable-list {
  padding: 1.5rem;
}

code {
  font-family: 'Courier New', monospace;
}
</style>
