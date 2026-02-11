<template>
  <div class="prompt-set-detail">
    <LoadingContainer :loading="loading">
      <!-- 头部信息 -->
      <PageCard v-if="promptSet" :title="promptSet.name">
        <template #header-right>
          <div class="flex gap-2">
            <button class="btn btn-ghost btn-sm" @click="handleBack">
              返回列表
            </button>
            <button class="btn btn-primary btn-sm" @click="handleEdit">
              编辑
            </button>
            <div class="dropdown dropdown-end">
              <label tabindex="0" class="btn btn-ghost btn-sm">
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
                <li v-if="!promptSet.is_default && isAdmin">
                  <a @click="handleSetDefault">设为默认</a>
                </li>
                <li><a @click="handleClone">克隆</a></li>
                <li><a @click="handleToggleActive">{{ promptSet.is_active ? '停用' : '启用' }}</a></li>
                <li class="text-error">
                  <a @click="handleDelete">删除</a>
                </li>
              </ul>
            </div>
          </div>
        </template>

        <!-- 基本信息 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <!-- 描述 -->
          <div class="lg:col-span-2 card bg-base-100 border border-base-300">
            <div class="card-body">
              <h3 class="text-sm font-semibold text-base-content/60 mb-2">描述</h3>
              <p class="text-base-content">{{ promptSet.description || '暂无描述' }}</p>
            </div>
          </div>

          <!-- 状态信息 -->
          <div class="card bg-base-100 border border-base-300">
            <div class="card-body">
              <h3 class="text-sm font-semibold text-base-content/60 mb-4">状态信息</h3>
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-base-content/60">状态</span>
                  <StatusBadge :status="promptSet.is_active ? '激活' : '未激活'" />
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-base-content/60">默认</span>
                  <div class="badge badge-sm" :class="promptSet.is_default ? 'badge-primary' : 'badge-ghost'">
                    {{ promptSet.is_default ? '是' : '否' }}
                  </div>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-base-content/60">模板数</span>
                  <span class="font-semibold">{{ promptSet.templates_count || 0 }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-base-content/60">创建者</span>
                  <span>{{ promptSet.created_by?.username || '未知' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 提示词模板列表 -->
        <div class="card bg-base-100 border border-base-300">
          <div class="card-body">
            <div class="flex items-center justify-between mb-4">
              <h3 class="card-title text-base">提示词模板</h3>
              <button class="btn btn-primary btn-sm" @click="handleCreateTemplate">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5 mr-1"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                    clip-rule="evenodd"
                  />
                </svg>
                添加模板
              </button>
            </div>

            <!-- 模板列表 -->
            <div v-if="templates.length > 0" class="space-y-3">
              <div
                v-for="template in templates"
                :key="template.id"
                class="card bg-base-200/50 border border-base-300 hover:border-primary transition-colors"
              >
                <div class="card-body p-4">
                  <div class="flex items-start justify-between">
                    <div class="flex-1">
                      <div class="flex items-center gap-2 mb-2">
                        <h4 class="font-semibold">{{ template.stage_type_display }}</h4>
                        <div class="badge badge-sm">v{{ template.version }}</div>
                        <StatusBadge :status="template.is_active ? '激活' : '未激活'" size="sm" />
                      </div>
                      <p class="text-sm text-base-content/60 line-clamp-2">
                        {{ template.template_content }}
                      </p>
                      <div class="text-xs text-base-content/40 mt-2">
                        更新于 {{ formatDate(template.updated_at) }}
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <!-- 激活状态切换开关 -->
                      <div class="form-control">
                        <label class="label cursor-pointer gap-2">
                          <span class="label-text text-xs">启用</span>
                          <input
                            type="checkbox"
                            class="toggle toggle-primary toggle-sm"
                            :checked="template.is_active"
                            @change="handleToggleTemplateActive(template)"
                            :disabled="updatingTemplateId === template.id"
                            title="切换激活状态"
                          />
                        </label>
                      </div>
                      <div class="divider divider-horizontal mx-0"></div>
                      <button
                        class="btn btn-ghost btn-sm"
                        @click="handleEditTemplate(template)"
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
                        class="btn btn-ghost btn-sm text-error"
                        @click="handleDeleteTemplate(template)"
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
                  </div>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else class="text-center py-8">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-12 w-12 mx-auto text-base-300"
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
              <p class="mt-4 text-base-content/60">暂无模板</p>
              <button class="btn btn-primary btn-sm mt-4" @click="handleCreateTemplate">
                创建第一个模板
              </button>
            </div>
          </div>
        </div>
      </PageCard>

      <!-- 未找到提示词集 -->
      <div v-else-if="!loading" class="text-center py-12">
        <p class="text-base-content/60">未找到该提示词集</p>
        <button class="btn btn-primary btn-sm mt-4" @click="handleBack">返回列表</button>
      </div>
    </LoadingContainer>

    <!-- 克隆对话框 -->
    <dialog ref="cloneDialog" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">克隆提示词集</h3>
        <p class="py-4">请为新的提示词集输入名称:</p>
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

    <!-- 创建模板对话框 -->
    <dialog ref="createTemplateDialog" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">选择模板阶段</h3>
        <p class="py-4">请选择要创建的模板阶段类型:</p>
        <div class="form-control">
          <select v-model="newTemplateStage" class="select select-bordered">
            <option value="">请选择...</option>
            <option v-for="stage in stageTypes" :key="stage.value" :value="stage.value">
              {{ stage.label }}
            </option>
          </select>
        </div>
        <div class="modal-action">
          <button class="btn" @click="$refs.createTemplateDialog.close()">取消</button>
          <button class="btn btn-primary" @click="confirmCreateTemplate" :disabled="!newTemplateStage">
            继续
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
import { mapState, mapGetters, mapActions } from 'vuex';
import PageCard from '@/components/common/PageCard.vue';
import StatusBadge from '@/components/common/StatusBadge.vue';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { formatDate } from '@/utils/helpers';
import { STAGE_TYPES } from '@/api/prompts';

export default {
  name: 'PromptSetDetail',
  components: {
    PageCard,
    StatusBadge,
    LoadingContainer,
  },
  data() {
    return {
      loading: false,
      cloneName: '',
      newTemplateStage: '',
      stageTypes: STAGE_TYPES,
      updatingTemplateId: null, // 正在更新的模板ID
    };
  },
  computed: {
    ...mapState('prompts', {
      promptSet: (state) => state.currentPromptSet,
    }),
    ...mapGetters('auth', {
      currentUser: 'currentUser',
    }),
    isAdmin() {
      return this.currentUser?.is_staff || false;
    },
    templates() {
      // 直接从提示词集详情中获取模板列表
      if (!this.promptSet || !this.promptSet.templates) return [];
      return this.promptSet.templates;
    },
  },
  async created() {
    await this.loadData();
  },
  methods: {
    ...mapActions('prompts', [
      'fetchPromptSetDetail',
      'clonePromptSet',
      'setDefaultPromptSet',
      'updatePromptSet',
      'deletePromptSet',
      'deletePromptTemplate',
      'partialUpdatePromptTemplate',
    ]),
    formatDate,

    async loadData() {
      this.loading = true;
      try {
        const id = this.$route.params.id;
        // 只加载提示词集详情（包含模板列表）
        await this.fetchPromptSetDetail(id);
      } catch (error) {
        console.error('加载数据失败:', error);
      } finally {
        this.loading = false;
      }
    },

    handleBack() {
      this.$router.push('/prompts');
    },

    handleEdit() {
      this.$router.push(`/prompts/sets/${this.$route.params.id}/edit`);
    },

    handleClone() {
      this.cloneName = `${this.promptSet.name} (副本)`;
      this.$refs.cloneDialog.showModal();
    },

    async confirmClone() {
      if (!this.cloneName) return;

      try {
        const newSet = await this.clonePromptSet({
          id: this.$route.params.id,
          name: this.cloneName,
        });
        this.$refs.cloneDialog.close();
        // 跳转到新的提示词集
        this.$router.push(`/prompts/sets/${newSet.id}`);
      } catch (error) {
        console.error('克隆提示词集失败:', error);
        alert('克隆失败,请重试');
      }
    },

    async handleSetDefault() {
      try {
        await this.setDefaultPromptSet(this.$route.params.id);
        await this.loadData();
      } catch (error) {
        console.error('设置默认提示词集失败:', error);
        alert('设置默认失败,请重试');
      }
    },

    async handleToggleActive() {
      try {
        await this.updatePromptSet({
          id: this.$route.params.id,
          data: { is_active: !this.promptSet.is_active },
        });
        await this.loadData();
      } catch (error) {
        console.error('更新状态失败:', error);
        alert('更新状态失败,请重试');
      }
    },

    async handleDelete() {
      if (!confirm(`确定要删除提示词集 "${this.promptSet.name}" 吗?此操作不可恢复。`)) {
        return;
      }

      try {
        await this.deletePromptSet(this.$route.params.id);
        this.$router.push('/prompts');
      } catch (error) {
        console.error('删除提示词集失败:', error);
        alert('删除失败,请重试');
      }
    },

    handleCreateTemplate() {
      this.newTemplateStage = '';
      this.$refs.createTemplateDialog.showModal();
    },

    confirmCreateTemplate() {
      if (!this.newTemplateStage) return;

      this.$refs.createTemplateDialog.close();
      // 跳转到模板编辑器,使用查询参数传递提示词集ID和阶段类型
      this.$router.push({
        path: '/prompts/templates/create',
        query: {
          template_set: this.$route.params.id,
          stage_type: this.newTemplateStage,
        },
      });
    },

    handleEditTemplate(template) {
      this.$router.push(`/prompts/templates/${template.id}/edit`);
    },

    async handleDeleteTemplate(template) {
      if (!confirm(`确定要删除 "${template.stage_type_display}" 模板吗?`)) {
        return;
      }

      try {
        await this.deletePromptTemplate(template.id);
        await this.loadData();
      } catch (error) {
        console.error('删除模板失败:', error);
        alert('删除模板失败,请重试');
      }
    },

    async handleToggleTemplateActive(template) {
      // 防止重复点击
      if (this.updatingTemplateId === template.id) {
        return;
      }

      this.updatingTemplateId = template.id;
      try {
        // 调用 API 更新状态,Vuex 会自动更新 store 中的数据
        await this.partialUpdatePromptTemplate({
          id: template.id,
          data: { is_active: !template.is_active },
        });
        // 不需要重新加载整个页面,Vuex mutation 已经更新了状态
      } catch (error) {
        console.error('更新模板激活状态失败:', error);
        alert('更新激活状态失败,请重试');
        // 如果失败,重新加载数据以恢复正确状态
        await this.loadData();
      } finally {
        this.updatingTemplateId = null;
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
