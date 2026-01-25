<template>
  <div class="project-list p-6">
    <page-card title="项目列表">
      <template slot="header-right">
        <button class="btn btn-primary btn-sm gap-2" @click="handleCreate">
          创建项目
        </button>
      </template>

      <!-- 筛选区域 -->
      <div class="flex flex-wrap gap-3 mb-6">
        <div class="form-control">
          <div class="input-group">
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索项目名称"
              class="input input-bordered input-sm w-48"
              @keyup.enter="handleFilter"
            />
            <button class="btn btn-square btn-sm" @click="handleFilter">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
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
            </button>
          </div>
        </div>
        <select
          v-model="filters.status"
          class="select select-bordered select-sm w-32"
          @change="handleFilter"
        >
          <option value="">全部状态</option>
          <option value="draft">草稿</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
          <option value="paused">已暂停</option>
        </select>
      </div>

      <!-- 项目列表 -->
      <loading-container :loading="loading">
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr>
                <th class="w-1/4">项目名称</th>
                <th class="w-2/5">描述</th>
                <th class="w-28">状态</th>
                <th class="w-40">创建时间</th>
                <th class="w-48">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in projects" :key="project.id">
                <td>
                  <a
                    href="#"
                    class="link link-primary font-medium"
                    @click.prevent="handleView(project.id)"
                  >
                    {{ project.name }}
                  </a>
                </td>
                <td>
                  <div class="truncate max-w-md" :title="project.description">
                    {{ project.description }}
                  </div>
                </td>
                <td>
                  <status-badge :status="project.status" type="project" />
                </td>
                <td>{{ formatDate(project.created_at) }}</td>
                <td>
                  <div class="flex gap-2 flex-wrap">
                    <button
                      class="btn btn-ghost btn-xs"
                      @click="handleView(project.id)"
                    >
                      查看
                    </button>
                    <button
                      class="btn btn-ghost btn-xs text-error"
                      @click="handleDelete(project)"
                    >
                      删除
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="projects.length === 0">
                <td colspan="5" class="text-center text-base-content/60 py-8">
                  暂无数据
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div class="flex justify-end mt-6">
          <div class="btn-group">
            <button
              class="btn btn-sm"
              :disabled="pagination.page === 1"
              @click="handlePageChange(pagination.page - 1)"
            >
              «
            </button>
            <button class="btn btn-sm">
              第 {{ pagination.page }} 页 / 共 {{ totalPages }} 页
            </button>
            <button
              class="btn btn-sm"
              :disabled="pagination.page >= totalPages"
              @click="handlePageChange(pagination.page + 1)"
            >
              »
            </button>
          </div>
        </div>
      </loading-container>
    </page-card>

    <!-- 删除确认模态框 -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">确认删除</h3>
        <p class="py-4">
          确定要删除项目 <span class="font-semibold">"{{ deletingProject?.name }}"</span> 吗?
        </p>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="closeDeleteModal">取消</button>
          <button class="btn btn-error" @click="confirmDelete">删除</button>
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
import PageCard from '@/components/common/PageCard.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import JianyingDraftButton from '@/components/projects/JianyingDraftButton.vue';
import { formatDate } from '@/utils/helpers';

export default {
  name: 'ProjectList',
  components: {
    PageCard,
    StatusBadge,
    LoadingContainer,
    JianyingDraftButton,
  },
  data() {
    return {
      loading: false,
      filters: {
        search: '',
        status: '',
      },
      deletingProject: null,
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

    handleEdit(id) {
      this.$router.push(`/projects/${id}/edit`);
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
        // 显示成功消息 (需要实现全局通知组件)
        console.log('删除成功');
      } catch (error) {
        console.error('Failed to delete project:', error);
      }
    },

    handleDraftGenerated(project, data) {
      console.log('剪映草稿生成成功:', data);
      // 更新项目数据（可选）
      // 可以显示成功提示
      alert(`剪映草稿生成成功！\n路径: ${data.draftPath}\n视频数量: ${data.videoCount}`);

      // 刷新项目列表以更新jianying_draft_path字段
      this.fetchData();
    },
  },
};
</script>

<style scoped>
/* 额外样式 */
</style>
