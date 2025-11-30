<template>
  <div class="container mx-auto px-4 py-6">
    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center items-center min-h-screen">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <!-- 项目内容 -->
    <div v-else-if="project" class="space-y-6">
      <!-- 页面标题和操作 -->
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold">{{ project.name }}</h1>
          <p class="text-base-content/70 mt-2">{{ project.description || '暂无描述' }}</p>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-outline" @click="handleEdit">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            编辑
          </button>
          <button class="btn btn-sm btn-error btn-outline" @click="handleDelete">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            删除
          </button>
        </div>
      </div>

      <!-- 工作流进度 -->
      <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title">工作流进度</h2>

          <!-- 进度条 -->
          <div class="mb-6">
            <div class="flex justify-between text-sm mb-2">
              <span>总体进度</span>
              <span class="font-semibold">{{ progressPercentage }}%</span>
            </div>
            <progress
              class="progress progress-primary w-full"
              :value="progressPercentage"
              max="100"
            ></progress>
          </div>

          <!-- 阶段列表 -->
          <div class="space-y-4">
            <div
              v-for="(stage, index) in stages"
              :key="stage.id"
              class="card bg-base-200"
            >
              <div class="card-body p-4">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-4 flex-1">
                    <!-- 阶段序号 -->
                    <div class="badge badge-lg" :class="getStageBadgeClass(stage.status)">
                      {{ index + 1 }}
                    </div>

                    <!-- 阶段信息 -->
                    <div class="flex-1">
                      <h3 class="font-semibold">{{ stage.stage_type_display }}</h3>
                      <div class="flex items-center gap-2 mt-1">
                        <span class="badge badge-sm" :class="getStatusBadgeClass(stage.status)">
                          {{ stage.status_display }}
                        </span>
                        <span v-if="stage.retry_count > 0" class="text-xs text-base-content/60">
                          重试: {{ stage.retry_count }}/{{ stage.max_retries }}
                        </span>
                      </div>
                    </div>

                    <!-- 时间信息 -->
                    <div class="text-xs text-base-content/60 text-right">
                      <div v-if="stage.started_at">
                        开始: {{ formatTime(stage.started_at) }}
                      </div>
                      <div v-if="stage.completed_at">
                        完成: {{ formatTime(stage.completed_at) }}
                      </div>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="flex gap-2">
                    <button
                      v-if="stage.status === 'pending'"
                      class="btn btn-sm btn-primary"
                      @click="handleExecuteStage(stage.stage_type)"
                      :disabled="executing"
                    >
                      执行
                    </button>
                    <button
                      v-if="stage.status === 'failed' && stage.retry_count < stage.max_retries"
                      class="btn btn-sm btn-warning"
                      @click="handleRetryStage(stage.stage_type)"
                      :disabled="executing"
                    >
                      重试
                    </button>
                    <button
                      v-if="stage.status === 'completed'"
                      class="btn btn-sm btn-ghost"
                      @click="handleRollbackStage(stage.stage_type)"
                      :disabled="executing"
                    >
                      回滚
                    </button>
                  </div>
                </div>

                <!-- 错误信息 -->
                <div v-if="stage.error_message" class="alert alert-error mt-2">
                  <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span class="text-sm">{{ stage.error_message }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 项目信息卡片 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 基本信息 -->
        <div class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <h2 class="card-title">基本信息</h2>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-base-content/70">状态</span>
                <span class="badge" :class="getProjectStatusBadgeClass(project.status)">
                  {{ project.status_display }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-base-content/70">提示词集</span>
                <span>{{ project.prompt_set_name || '默认' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-base-content/70">创建时间</span>
                <span>{{ formatDate(project.created_at) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-base-content/70">更新时间</span>
                <span>{{ formatDate(project.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="card bg-base-100 shadow-xl">
          <div class="card-body">
            <h2 class="card-title">统计信息</h2>
            <div class="stats stats-vertical shadow">
              <div class="stat">
                <div class="stat-title">已完成阶段</div>
                <div class="stat-value text-primary">{{ project.completed_stages }}</div>
                <div class="stat-desc">共 {{ project.total_stages }} 个阶段</div>
              </div>
              <div class="stat">
                <div class="stat-title">失败阶段</div>
                <div class="stat-value text-error">{{ project.failed_stages }}</div>
                <div class="stat-desc">{{ project.failed_stages > 0 ? '需要处理' : '一切正常' }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 原始主题 -->
      <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title">原始主题/文案</h2>
          <div class="prose max-w-none">
            <p class="whitespace-pre-wrap">{{ project.original_topic }}</p>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <h2 class="card-title">项目操作</h2>
          <div class="flex gap-2 flex-wrap">
            <button
              v-if="project.status === 'paused'"
              class="btn btn-success"
              @click="handleResume"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              恢复项目
            </button>
            <button
              v-if="project.status === 'processing'"
              class="btn btn-warning"
              @click="handlePause"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              暂停项目
            </button>
            <button
              v-if="project.status === 'completed'"
              class="btn btn-primary"
              @click="handleExport"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              导出项目
            </button>
            <button
              class="btn btn-outline"
              @click="handleSaveAsTemplate"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              保存为模板
            </button>

            <!-- 剪映草稿生成按钮 -->
            <jianying-draft-button
              v-if="project"
              :project-id="project.id"
              :project="project"
              @generated="handleDraftGenerated"
            />
          </div>

          <!-- 剪映草稿路径显示 -->
          <div v-if="project?.jianying_draft_path" class="alert alert-info mt-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <div class="font-bold">剪映草稿已生成</div>
              <div class="text-sm">路径: {{ project.jianying_draft_path }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>项目不存在或加载失败</span>
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex';
import JianyingDraftButton from '@/components/projects/JianyingDraftButton.vue';

export default {
  name: 'ProjectDetail',
  components: {
    JianyingDraftButton,
  },
  data() {
    return {
      loading: true,
      executing: false,
    };
  },
  computed: {
    ...mapState('projects', ['currentProject', 'stages']),
    ...mapGetters('projects', ['progressPercentage']),

    project() {
      return this.currentProject;
    },
  },
  async created() {
    await this.loadProject();
  },
  methods: {
    ...mapActions('projects', [
      'fetchProject',
      'fetchProjectStages',
      'deleteProject',
      'executeStage',
      'retryStage',
      'rollbackStage',
      'pauseProject',
      'resumeProject',
    ]),

    async loadProject() {
      const projectId = this.$route.params.id;
      this.loading = true;
      try {
        await this.fetchProject(projectId);
        await this.fetchProjectStages(projectId);
      } catch (error) {
        console.error('加载项目失败:', error);
      } finally {
        this.loading = false;
      }
    },

    handleEdit() {
      this.$router.push({
        name: 'ProjectEdit',
        params: { id: this.project.id },
      });
    },

    async handleDelete() {
      if (!confirm(`确定要删除项目"${this.project.name}"吗？此操作不可恢复。`)) {
        return;
      }

      try {
        await this.deleteProject(this.project.id);
        alert('✓ 项目已删除');
        this.$router.push({ name: 'ProjectList' });
      } catch (error) {
        console.error('删除项目失败:', error);
        alert('✗ 删除项目失败');
      }
    },

    async handleExecuteStage(stageName) {
      this.executing = true;
      try {
        await this.executeStage({
          projectId: this.project.id,
          stageName,
        });
        alert(`✓ 阶段 ${stageName} 开始执行`);
      } catch (error) {
        console.error('执行阶段失败:', error);
        alert('✗ 执行阶段失败');
      } finally {
        this.executing = false;
      }
    },

    async handleRetryStage(stageName) {
      this.executing = true;
      try {
        await this.retryStage({
          projectId: this.project.id,
          stageName,
        });
        alert(`✓ 阶段 ${stageName} 开始重试`);
      } catch (error) {
        console.error('重试阶段失败:', error);
        alert('✗ 重试阶段失败');
      } finally {
        this.executing = false;
      }
    },

    async handleRollbackStage(stageName) {
      if (!confirm(`确定要回滚到"${stageName}"阶段吗？后续阶段的数据将被清除。`)) {
        return;
      }

      this.executing = true;
      try {
        await this.rollbackStage({
          projectId: this.project.id,
          stageName,
        });
        alert(`✓ 已回滚到 ${stageName} 阶段`);
      } catch (error) {
        console.error('回滚阶段失败:', error);
        alert('✗ 回滚阶段失败');
      } finally {
        this.executing = false;
      }
    },

    async handlePause() {
      try {
        await this.pauseProject(this.project.id);
        alert('✓ 项目已暂停');
      } catch (error) {
        console.error('暂停项目失败:', error);
        alert('✗ 暂停项目失败');
      }
    },

    async handleResume() {
      try {
        await this.resumeProject(this.project.id);
        alert('✓ 项目已恢复');
      } catch (error) {
        console.error('恢复项目失败:', error);
        alert('✗ 恢复项目失败');
      }
    },

    handleExport() {
      alert('导出功能开发中...');
    },

    handleSaveAsTemplate() {
      const templateName = prompt('请输入模板名称:');
      if (templateName) {
        alert(`模板"${templateName}"保存功能开发中...`);
      }
    },

    handleDraftGenerated(data) {
      console.log('剪映草稿生成成功:', data);

      // 显示成功提示
      alert(`✓ 剪映草稿生成成功！\n路径: ${data.draftPath}\n视频数量: ${data.videoCount}`);

      // 刷新项目数据以更新 jianying_draft_path 字段
      this.loadProject();
    },

    getStageBadgeClass(status) {
      const map = {
        pending: 'badge-ghost',
        processing: 'badge-info',
        completed: 'badge-success',
        failed: 'badge-error',
      };
      return map[status] || 'badge-ghost';
    },

    getStatusBadgeClass(status) {
      const map = {
        pending: 'badge-ghost',
        processing: 'badge-info',
        completed: 'badge-success',
        failed: 'badge-error',
      };
      return map[status] || 'badge-ghost';
    },

    getProjectStatusBadgeClass(status) {
      const map = {
        draft: 'badge-ghost',
        processing: 'badge-info',
        completed: 'badge-success',
        failed: 'badge-error',
        paused: 'badge-warning',
      };
      return map[status] || 'badge-ghost';
    },

    formatDate(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN');
    },

    formatTime(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
  },
};
</script>
