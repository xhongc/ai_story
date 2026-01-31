<template>
  <div class="prompt-list p-6">
    <!-- 页面头部 -->
    <PageCard title="提示词管理">
      <template slot="header-right">
        <button class="btn btn-primary btn-sm" @click="handleCreate">
          +
          创建提示词集
        </button>
      </template>

      <!-- 搜索和过滤 -->
      <div class="mb-6 flex gap-4">
        <div class="form-control flex-1">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索提示词集..."
            class="input input-bordered w-full"
            @input="handleSearch"
          />
        </div>
        <div class="form-control">
          <select v-model="filterStatus" class="select select-bordered" @change="handleFilter">
            <option value="">全部状态</option>
            <option value="active">仅激活</option>
            <option value="inactive">仅停用</option>
          </select>
        </div>
        <div class="form-control">
          <select v-model="filterDefault" class="select select-bordered" @change="handleFilter">
            <option value="">全部</option>
            <option value="true">仅默认</option>
            <option value="false">非默认</option>
          </select>
        </div>
      </div>

      <!-- Loading状态 -->
      <LoadingContainer :loading="loading">
        <!-- 空状态 -->
        <div v-if="!loading && promptSets.length === 0" class="text-center py-12">
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p class="mt-4 text-base-content/60">暂无提示词集</p>
          <button class="btn btn-primary btn-sm mt-4" @click="handleCreate">创建第一个提示词集</button>
        </div>

        <!-- 卡片网格 -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="set in promptSets"
            :key="set.id"
            class="card bg-base-100 shadow-md hover:shadow-xl transition-shadow border border-base-300"
          >
            <!-- 卡片头部 -->
            <div class="card-body">
              <div class="flex items-start justify-between">
                <h2 class="card-title text-lg">
                  {{ set.name }}
                  <div class="badge badge-primary badge-sm" v-if="set.is_default">默认</div>
                </h2>
                <StatusBadge :status="set.is_active ? 'active' : 'inactive'" />
              </div>

              <p class="text-sm text-base-content/60 line-clamp-2">
                {{ set.description || '暂无描述' }}
              </p>

              <!-- 统计信息 -->
              <div class="flex gap-4 mt-4 text-sm">
                <div class="flex items-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"
                    />
                    <path
                      fill-rule="evenodd"
                      d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <span>{{ set.templates_count || 0 }} 个模板</span>
                </div>
                <div class="flex items-center gap-1 text-base-content/50">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <span>{{ set.created_by?.username || '未知' }}</span>
                </div>
              </div>

              <!-- 时间信息 -->
              <div class="text-xs text-base-content/40 mt-2">
                更新于 {{ formatDate(set.updated_at) }}
              </div>

              <!-- 操作按钮 -->
              <div class="card-actions justify-end mt-4 flex-wrap gap-2">
                <button class="btn btn-sm btn-ghost" @click="handleView(set)">
                  编辑
                </button>
                <div class="dropdown dropdown-end">
                  <label tabindex="0" class="btn btn-sm btn-ghost">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"
                      />
                    </svg>
                  </label>
                  <ul
                    tabindex="0"
                    class="dropdown-content z-[1] menu p-2 shadow-lg bg-base-100 rounded-box w-52 border border-base-300"
                  >
                    <li v-if="!set.is_default">
                      <a @click="handleSetDefault(set)">设为默认</a>
                    </li>
                    <li><a @click="handleClone(set)">克隆</a></li>
                    <li><a @click="handleEdit(set)">编辑描述</a></li>
                    <li><a @click="handleToggleActive(set)">{{ set.is_active ? '停用' : '启用' }}</a></li>
                    <li class="text-error">
                      <a @click="handleDelete(set)">删除</a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="flex justify-center mt-8">
          <div class="join">
            <button
              class="join-item btn btn-sm"
              :disabled="currentPage === 1"
              @click="handlePageChange(currentPage - 1)"
            >
              «
            </button>
            <button class="join-item btn btn-sm">第 {{ currentPage }} 页</button>
            <button
              class="join-item btn btn-sm"
              :disabled="currentPage * pageSize >= total"
              @click="handlePageChange(currentPage + 1)"
            >
              »
            </button>
          </div>
        </div>
      </LoadingContainer>
    </PageCard>

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
import PageCard from '@/components/common/PageCard.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'PromptList',
  components: {
    PageCard,
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

    handlePageChange(page) {
      this.currentPage = page;
      this.fetchData();
    },

    handleCreate() {
      this.$router.push('/prompts/sets/create');
    },

    handleView(set) {
      this.$router.push(`/prompts/sets/${set.id}`);
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
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
