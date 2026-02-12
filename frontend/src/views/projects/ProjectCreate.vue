<template>
  <div class="w-full px-4 py-6">
    <!-- 页面标题 -->
    <div class="mb-6">
      <h1 class="text-3xl font-bold">创建项目</h1>
      <p class="text-base-content/70 mt-2">填写项目基本信息，开始你的AI Story创作之旅</p>
    </div>

    <!-- 表单卡片 -->
    <div class="card bg-base-100 shadow-xl w-full">
      <div class="card-body">
        <form @submit.prevent="handleSubmit">
          <!-- 项目名称 -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text font-semibold">
                项目名称 <span class="text-error">*</span>
              </span>
            </label>
            <input
              v-model="form.name"
              type="text"
              placeholder="请输入项目名称"
              class="input input-bordered w-full"
              :class="{ 'input-error': errors.name }"
              required
            />
            <label v-if="errors.name" class="label">
              <span class="label-text-alt text-error">{{ errors.name }}</span>
            </label>
          </div>

          <!-- 项目描述 -->
          <div class="form-control w-full mt-4">
            <label class="label">
              <span class="label-text font-semibold">项目描述</span>
              <span class="label-text-alt text-base-content/60">选填</span>
            </label>
            <textarea
              v-model="form.description"
              class="textarea textarea-bordered h-24"
              placeholder="简要描述你的项目..."
            ></textarea>
          </div>

          <!-- 原始主题 -->
          <div class="form-control w-full mt-4">
            <label class="label">
              <span class="label-text font-semibold">
                原始主题/文案 <span class="text-error">*</span>
              </span>
              <span class="label-text-alt text-base-content/60">
                字数: {{ form.original_topic.length }}
              </span>
            </label>
            <textarea
              v-model="form.original_topic"
              class="textarea textarea-bordered h-40"
              :class="{ 'textarea-error': errors.original_topic }"
              placeholder="请输入原始主题或文案内容...&#10;&#10;示例：&#10;讲述一个关于人工智能觉醒的故事，主角是一个在未来世界中工作的程序员..."
              required
            ></textarea>
            <label v-if="errors.original_topic" class="label">
              <span class="label-text-alt text-error">{{ errors.original_topic }}</span>
            </label>
          </div>

          <!-- 提示词集选择 -->
          <div class="form-control w-full mt-4">
            <label class="label">
              <span class="label-text font-semibold">提示词集</span>
              <span class="label-text-alt text-base-content/60">可选，留空使用默认</span>
            </label>
            <select
              v-model="form.prompt_template_set"
              class="select select-bordered w-full"
              :disabled="loadingTemplates"
            >
              <option :value="null">
                {{ loadingTemplates ? '加载中...' : '使用默认提示词集' }}
              </option>
              <option v-for="set in templateSets" :key="set.id" :value="set.id">
                {{ set.name }}
                {{ set.is_default ? ' (默认)' : '' }}
                {{ set.templates_count ? ` - ${set.templates_count}个模板` : '' }}
              </option>
            </select>
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                <template v-if="selectedTemplateSetInfo">
                  {{ selectedTemplateSetInfo }}
                </template>
                <template v-else>
                  提示词集控制AI如何理解和处理你的内容
                </template>
              </span>
            </label>
          </div>
          <!-- 按钮组 -->
          <div class="card-actions justify-end mt-8">
            <button
              type="button"
              class="btn btn-ghost btn-sm"
              @click="handleCancel"
              :disabled="submitting"
            >
              取消
            </button>
            <button type="submit" class="btn btn-primary btn-sm" :disabled="submitting">
              <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
              <span v-if="!submitting">
                创建项目
              </span>
              <span v-else>创建中...</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { mapActions } from 'vuex';
import { promptSetAPI } from '@/api/prompts';

export default {
  name: 'ProjectCreate',
  data() {
    return {
      form: {
        name: '',
        description: '',
        original_topic: '',
        prompt_template_set: null,
      },
      errors: {
        name: '',
        original_topic: '',
      },
      templateSets: [],
      loadingTemplates: false,
      submitting: false,
    };
  },
  computed: {
    /**
     * 获取当前选中的提示词集信息
     * 用于显示描述和提示
     */
    selectedTemplateSetInfo() {
      if (!this.form.prompt_template_set) {
        return '';
      }
      const selected = this.templateSets.find(
        (set) => set.id === this.form.prompt_template_set
      );
      return selected?.description || '';
    },
  },
  created() {
    this.fetchTemplateSets();
  },
  methods: {
    ...mapActions('projects', ['createProject']),

    async fetchTemplateSets() {
      this.loadingTemplates = true;
      try {
        // 调用后端API获取提示词集列表
        // 只获取激活的提示词集,用于项目创建选择
        const response = await promptSetAPI.getList({
          is_active: true,
          page_size: 100  // 获取所有激活的提示词集
        });

        // DRF分页响应格式: {count, next, previous, results}
        // 或非分页直接返回数组
        console.log(133333, response)
        this.templateSets = response.results || response || [];
        console.log('成功加载提示词集:', this.templateSets.length, '个');
      } catch (error) {
        console.error('获取提示词集失败:', error);
        const errorMsg = error.response?.data?.message || error.message || '获取提示词集失败';
        this.showToast(errorMsg, 'error');
        // 失败时使用空数组,让用户可以选择使用默认提示词集
        this.templateSets = [];
      } finally {
        this.loadingTemplates = false;
      }
    },

    validateForm() {
      let isValid = true;
      this.errors = {
        name: '',
        original_topic: '',
      };

      if (!this.form.name || !this.form.name.trim()) {
        this.errors.name = '请输入项目名称';
        isValid = false;
      } else if (this.form.name.length > 255) {
        this.errors.name = '项目名称不能超过255个字符';
        isValid = false;
      }

      if (!this.form.original_topic || !this.form.original_topic.trim()) {
        this.errors.original_topic = '请输入原始主题或文案';
        isValid = false;
      } else if (this.form.original_topic.length < 10) {
        this.errors.original_topic = '内容至少需要10个字符';
        isValid = false;
      }

      return isValid;
    },

    async handleSubmit() {
      if (!this.validateForm()) {
        return;
      }

      this.submitting = true;
      try {
        const projectData = {
          name: this.form.name.trim(),
          description: this.form.description.trim(),
          original_topic: this.form.original_topic.trim(),
          prompt_template_set: this.form.prompt_template_set,
        };

        const project = await this.createProject(projectData);

        // this.showToast('项目创建成功！', 'success');
        // 跳转到项目详情页
        setTimeout(() => {
          this.$router.push({
            name: 'ProjectDetail',
            params: { id: project.id },
          });
        }, 500);
      } catch (error) {
        console.error('创建项目失败:', error);
        const errorMsg = error.response?.data?.message || error.message || '创建项目失败';
        this.showToast(errorMsg, 'error');
      } finally {
        this.submitting = false;
      }
    },

    handleCancel() {
      // 检查表单是否有内容
      const hasContent =
        this.form.name || this.form.description || this.form.original_topic;

      if (hasContent) {
        if (confirm('确定要取消吗？已填写的内容将丢失。')) {
          this.$router.push({ name: 'ProjectList' });
        }
      } else {
        this.$router.push({ name: 'ProjectList' });
      }
    },

    showToast(message, type = 'info') {
      // TODO: 实现全局Toast组件后替换
      if (type === 'success') {
        alert(`✓ ${message}`);
      } else if (type === 'error') {
        alert(`✗ ${message}`);
      } else {
        alert(message);
      }
    },
  },
};
</script>

<style scoped>
/* 额外的样式调整 */
textarea.textarea {
  font-family: inherit;
  line-height: 1.6;
}

.alert ul {
  margin-left: 0.5rem;
}
</style>
