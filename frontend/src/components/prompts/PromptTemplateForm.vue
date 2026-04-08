<template>
  <div class="prompt-template-form">
    <div class="template-form-toolbar">
      <div class="template-form-toolbar__meta">
        <div class="template-form-toolbar__title">
          {{ resolvedToolbarTitle }}
        </div>
        <div class="template-form-toolbar__hint">
          {{ resolvedToolbarHint }}
        </div>
      </div>
      <div class="template-form-toolbar__actions">
        <button
          v-if="showCancel"
          type="button"
          class="btn btn-ghost btn-sm"
          @click="$emit('cancel')"
        >
          {{ cancelText }}
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm"
          :disabled="validating"
          @click="handleValidate"
        >
          <span
            v-if="validating"
            class="loading loading-spinner loading-sm"
          />
          验证语法
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm"
          :disabled="!canPreview"
          @click="handlePreview"
        >
          预览
        </button>
        <button
          type="button"
          class="btn btn-primary btn-sm"
          :disabled="submitting || !isFormValid"
          @click="handleSubmit"
        >
          <span
            v-if="submitting"
            class="loading loading-spinner loading-sm"
          />
          {{ submitTextComputed }}
        </button>
      </div>
    </div>

    <LoadingContainer :loading="loading">
      <form
        class="space-y-6"
        @submit.prevent="handleSubmit"
      >
        <div class="card bg-base-100 border border-base-300">
          <div class="card-body">
            <h3 class="card-title text-base mb-4">
              基本信息
            </h3>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="form-control">
                <label class="label">
                  <span class="label-text">
                    提示词集 <span class="text-error">*</span>
                  </span>
                </label>
                <select
                  v-model="formData.template_set"
                  class="select select-bordered"
                  :class="{ 'select-error': errors.template_set }"
                  :disabled="isTemplateSetDisabled"
                  required
                >
                  <option value="">
                    请选择提示词集
                  </option>
                  <option
                    v-for="set in promptSets"
                    :key="set.id"
                    :value="set.id"
                  >
                    {{ set.name }}
                  </option>
                </select>
                <label
                  v-if="errors.template_set"
                  class="label"
                >
                  <span class="label-text-alt text-error">{{ errors.template_set }}</span>
                </label>
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">
                    阶段类型 <span class="text-error">*</span>
                  </span>
                </label>
                <select
                  v-model="formData.stage_type"
                  class="select select-bordered"
                  :class="{ 'select-error': errors.stage_type }"
                  :disabled="isStageTypeDisabled"
                  required
                  @change="handleStageTypeChange"
                >
                  <option value="">
                    请选择阶段
                  </option>
                  <option
                    v-for="stage in stageTypes"
                    :key="stage.value"
                    :value="stage.value"
                  >
                    {{ stage.label }}
                  </option>
                </select>
                <label
                  v-if="errors.stage_type"
                  class="label"
                >
                  <span class="label-text-alt text-error">{{ errors.stage_type }}</span>
                </label>
              </div>
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">AI模型</span>
                <span class="label-text-alt text-base-content/60">
                  为此模板指定默认使用的AI模型
                </span>
              </label>
              <select
                v-model="formData.model_provider"
                class="select select-bordered"
                :class="{ 'select-error': errors.model_provider }"
                :disabled="!formData.stage_type || loadingModels"
              >
                <option value="">
                  无(使用项目配置)
                </option>
                <option
                  v-for="model in availableModels"
                  :key="model.id"
                  :value="model.id"
                >
                  {{ model.name }}
                </option>
              </select>
              <label class="label">
                <span class="label-text-alt text-base-content/60">
                  {{ getModelTypeHint() }}
                </span>
              </label>
              <label
                v-if="errors.model_provider"
                class="label"
              >
                <span class="label-text-alt text-error">{{ errors.model_provider }}</span>
              </label>
            </div>

            <div class="form-control">
              <label class="label cursor-pointer justify-start gap-4">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  class="checkbox checkbox-primary"
                >
                <span class="label-text">启用此模板</span>
              </label>
            </div>
          </div>
        </div>

        <div class="card bg-base-100 border border-base-300">
          <div class="card-body">
            <div class="flex items-center justify-between mb-4 gap-3 flex-wrap">
              <h3 class="card-title text-base">
                模板内容
              </h3>
              <div class="text-xs text-base-content/60">
                支持 Jinja2 语法,使用 <code>{{ sampleVariableToken }}</code> 引用变量
              </div>
            </div>

            <div class="form-control">
              <textarea
                v-model="formData.template_content"
                placeholder="请输入提示词模板内容..."
                class="textarea textarea-bordered font-mono text-sm h-64"
                :class="{ 'textarea-error': errors.template_content }"
                required
              />
              <label
                v-if="errors.template_content"
                class="label"
              >
                <span class="label-text-alt text-error">{{ errors.template_content }}</span>
              </label>
              <label class="label">
                <span class="label-text-alt">
                  已提取变量: {{ extractedVariables.length > 0 ? extractedVariables.join(', ') : '无' }}
                </span>
              </label>
            </div>
          </div>
        </div>

        <div class="card bg-base-100 border border-base-300">
          <div class="card-body">
            <div class="flex items-center justify-between mb-4 gap-3 flex-wrap">
              <h3 class="card-title text-base">
                变量定义
              </h3>
              <button
                type="button"
                class="btn btn-sm btn-ghost"
                @click="addVariable"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 mr-1"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                    clip-rule="evenodd"
                  />
                </svg>
                添加变量
              </button>
            </div>

            <div
              v-if="variableList.length > 0"
              class="space-y-3"
            >
              <div
                v-for="(variable, index) in variableList"
                :key="index"
                class="grid grid-cols-1 md:grid-cols-12 gap-3 items-start p-3 bg-base-200 rounded-lg"
              >
                <div class="md:col-span-5 form-control">
                  <input
                    v-model="variable.name"
                    type="text"
                    placeholder="变量名"
                    class="input input-bordered input-sm"
                  >
                </div>
                <div class="md:col-span-5 form-control">
                  <select
                    v-model="variable.type"
                    class="select select-bordered select-sm"
                  >
                    <option
                      v-for="type in variableTypes"
                      :key="type.value"
                      :value="type.value"
                    >
                      {{ type.label }}
                    </option>
                  </select>
                </div>
                <div class="md:col-span-2 flex items-center">
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm text-error"
                    @click="removeVariable(index)"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>

            <div
              v-else
              class="text-center py-8 text-base-content/60 text-sm"
            >
              暂无变量定义,点击“添加变量”按钮创建
            </div>

            <label
              v-if="errors.variables"
              class="label"
            >
              <span class="label-text-alt text-error">{{ errors.variables }}</span>
            </label>
          </div>
        </div>

        <div
          v-if="validationResult"
          class="alert"
          :class="validationResult.valid ? 'alert-success' : 'alert-error'"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              v-if="validationResult.valid"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
            <path
              v-else
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{{ validationResult.message }}</span>
        </div>

        <div
          v-if="formError"
          class="alert alert-error"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{{ formError }}</span>
        </div>

        <div
          v-if="formSuccess"
          class="alert alert-success"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="stroke-current shrink-0 h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{{ formSuccess }}</span>
        </div>
      </form>
    </LoadingContainer>

    <dialog
      ref="previewDialog"
      class="modal"
    >
      <div class="modal-box max-w-3xl">
        <h3 class="font-bold text-lg mb-4">
          模板预览
        </h3>

        <div
          v-if="variableList.length > 0"
          class="space-y-3 mb-6"
        >
          <h4 class="text-sm font-semibold text-base-content/60">
            输入变量值
          </h4>
          <div
            v-for="variable in variableList"
            :key="variable.name"
            class="form-control"
          >
            <label class="label">
              <span class="label-text">{{ variable.name }} ({{ variable.type }})</span>
            </label>
            <input
              v-model="previewVariables[variable.name]"
              type="text"
              :placeholder="`请输入 ${variable.name}`"
              class="input input-bordered input-sm"
            >
          </div>
        </div>

        <div
          v-if="previewResult"
          class="mb-4"
        >
          <h4 class="text-sm font-semibold text-base-content/60 mb-2">
            渲染结果
          </h4>
          <div class="p-4 bg-base-200 rounded-lg">
            <pre class="text-sm whitespace-pre-wrap">{{ previewResult.rendered_content }}</pre>
          </div>
        </div>

        <div
          v-if="previewError"
          class="alert alert-error mb-4"
        >
          <span>{{ previewError }}</span>
        </div>

        <div class="modal-action">
          <button
            class="btn"
            @click="$refs.previewDialog.close()"
          >
            关闭
          </button>
          <button
            class="btn btn-primary"
            :disabled="previewing"
            @click="executePreview"
          >
            <span
              v-if="previewing"
              class="loading loading-spinner loading-sm"
            />
            渲染预览
          </button>
        </div>
      </div>
      <form
        method="dialog"
        class="modal-backdrop"
      >
        <button>关闭</button>
      </form>
    </dialog>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import LoadingContainer from '@/components/common/LoadingContainer.vue';
import { STAGE_TYPES, VARIABLE_TYPES } from '@/api/prompts';
import { modelProviderApi } from '@/api/models';

export default {
  name: 'PromptTemplateForm',
  components: {
    LoadingContainer,
  },
  props: {
    templateId: {
      type: [String, Number],
      default: null,
    },
    initialTemplateSet: {
      type: [String, Number],
      default: '',
    },
    initialStageType: {
      type: String,
      default: '',
    },
    lockTemplateSet: {
      type: Boolean,
      default: false,
    },
    lockStageType: {
      type: Boolean,
      default: false,
    },
    showCancel: {
      type: Boolean,
      default: true,
    },
    cancelText: {
      type: String,
      default: '取消',
    },
    submitText: {
      type: String,
      default: '',
    },
    toolbarTitle: {
      type: String,
      default: '',
    },
    toolbarHint: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      formData: {
        template_set: '',
        stage_type: '',
        model_provider: '',
        template_content: '',
        variables: {},
        is_active: true,
      },
      variableList: [],
      errors: {},
      formError: '',
      formSuccess: '',
      loading: false,
      submitting: false,
      validating: false,
      previewing: false,
      loadingModels: false,
      validationResult: null,
      previewVariables: {},
      previewResult: null,
      previewError: '',
      stageTypes: STAGE_TYPES,
      variableTypes: VARIABLE_TYPES,
      availableModels: [],
      stageToProviderType: {
        rewrite: 'llm',
        asset_extraction: 'llm',
        storyboard: 'llm',
        image_generation: 'text2image',
        multi_grid_image: 'text2image',
        camera_movement: 'llm',
        video_generation: 'image2video',
        image_edit: 'image_edit',
      },
      sampleVariableToken: '{{ variable_name }}',
    };
  },
  computed: {
    ...mapState('prompts', {
      promptSets: (state) => state.promptSets,
      currentTemplate: (state) => state.currentPromptTemplate,
    }),
    isEdit() {
      return !!this.templateId;
    },
    submitTextComputed() {
      if (this.submitText) {
        return this.submitText;
      }
      return this.isEdit ? '保存模板' : '创建模板';
    },
    resolvedToolbarTitle() {
      if (this.toolbarTitle) {
        return this.toolbarTitle;
      }
      return this.isEdit ? '编辑提示词模板' : '创建提示词模板';
    },
    resolvedToolbarHint() {
      if (this.toolbarHint) {
        return this.toolbarHint;
      }
      return this.isEdit ? '修改当前阶段模板内容并即时保存。' : '创建一个新的阶段模板。';
    },
    isTemplateSetDisabled() {
      return this.lockTemplateSet || this.isEdit;
    },
    isStageTypeDisabled() {
      return this.lockStageType || this.isEdit;
    },
    isFormValid() {
      return (
        this.formData.template_set &&
        this.formData.stage_type &&
        this.formData.template_content.trim().length > 0
      );
    },
    extractedVariables() {
      const regex = /\{\{\s*(\w+)\s*\}\}/g;
      const matches = [];
      let match;
      while ((match = regex.exec(this.formData.template_content)) !== null) {
        if (!matches.includes(match[1])) {
          matches.push(match[1]);
        }
      }
      return matches;
    },
    canPreview() {
      return this.formData.template_content.trim().length > 0;
    },
  },
  watch: {
    variableList: {
      handler(newList) {
        const variables = {};
        newList.forEach((variable) => {
          if (variable.name) {
            variables[variable.name] = variable.type;
          }
        });
        this.formData.variables = variables;
      },
      deep: true,
    },
  },
  async created() {
    await this.initializeForm();
  },
  methods: {
    ...mapActions('prompts', [
      'fetchPromptSets',
      'fetchPromptTemplateDetail',
      'createPromptTemplate',
      'updatePromptTemplate',
      'validateTemplate',
      'previewTemplate',
    ]),

    async initializeForm() {
      this.resetFormState();
      await this.fetchPromptSets();
      this.applyInitialValues();

      if (this.formData.stage_type) {
        await this.loadAvailableModels(this.formData.stage_type);
      }

      if (this.isEdit) {
        await this.loadTemplate();
      }
    },

    resetFormState() {
      this.formData = {
        template_set: '',
        stage_type: '',
        model_provider: '',
        template_content: '',
        variables: {},
        is_active: true,
      };
      this.variableList = [];
      this.errors = {};
      this.formError = '';
      this.formSuccess = '';
      this.validationResult = null;
      this.previewVariables = {};
      this.previewResult = null;
      this.previewError = '';
      this.availableModels = [];
    },

    applyInitialValues() {
      if (this.initialTemplateSet !== '' && this.initialTemplateSet !== null && this.initialTemplateSet !== undefined) {
        this.formData.template_set = this.initialTemplateSet;
      }
      if (this.initialStageType) {
        this.formData.stage_type = this.initialStageType;
      }
      this.$emit('loaded', null);
    },

    async loadTemplate() {
      this.loading = true;
      try {
        await this.fetchPromptTemplateDetail(this.templateId);

        if (this.currentTemplate) {
          this.formData = {
            template_set: this.currentTemplate.template_set,
            stage_type: this.currentTemplate.stage_type,
            model_provider: this.currentTemplate.model_provider || '',
            template_content: this.currentTemplate.template_content,
            variables: this.currentTemplate.variables || {},
            is_active: this.currentTemplate.is_active,
          };

          this.variableList = Object.entries(this.currentTemplate.variables || {}).map(
            ([name, type]) => ({ name, type })
          );

          if (this.currentTemplate.stage_type) {
            await this.loadAvailableModels(this.currentTemplate.stage_type);
          }

          this.$emit('loaded', this.currentTemplate);
        }
      } catch (error) {
        console.error('加载模板失败:', error);
        this.formError = '加载模板失败,请重试';
      } finally {
        this.loading = false;
      }
    },

    async loadAvailableModels(stageType) {
      if (!stageType) {
        this.availableModels = [];
        return;
      }

      const providerType = this.stageToProviderType[stageType];
      if (!providerType) {
        console.warn('未知的阶段类型:', stageType);
        this.availableModels = [];
        return;
      }

      this.loadingModels = true;
      try {
        const response = await modelProviderApi.getSimpleList({
          provider_type: providerType,
        });

        this.availableModels = response.results || response || [];
      } catch (error) {
        console.error('加载模型列表失败:', error);
        this.formError = '加载模型列表失败';
        this.availableModels = [];
      } finally {
        this.loadingModels = false;
      }
    },

    async handleStageTypeChange() {
      this.formData.model_provider = '';
      await this.loadAvailableModels(this.formData.stage_type);
    },

    getModelTypeHint() {
      if (!this.formData.stage_type) {
        return '请先选择阶段类型';
      }

      const providerType = this.stageToProviderType[this.formData.stage_type];
      const typeLabels = {
        llm: 'LLM模型',
        text2image: '文生图模型',
        image2video: '图生视频模型',
        image_edit: '图片编辑模型',
      };

      return `当前阶段需要 ${typeLabels[providerType] || providerType} 类型的模型`;
    },

    addVariable() {
      this.variableList.push({ name: '', type: 'string' });
    },

    removeVariable(index) {
      this.variableList.splice(index, 1);
    },

    validateForm() {
      this.errors = {};
      this.formError = '';

      if (!this.formData.template_set) {
        this.errors.template_set = '请选择提示词集';
      }

      if (!this.formData.stage_type) {
        this.errors.stage_type = '请选择阶段类型';
      }

      if (!this.formData.template_content || this.formData.template_content.trim().length === 0) {
        this.errors.template_content = '请输入模板内容';
      }

      const hasEmptyVariable = this.variableList.some((variable) => !variable.name);
      if (hasEmptyVariable) {
        this.errors.variables = '存在未命名的变量';
      }

      const variableNames = this.variableList.map((variable) => variable.name).filter(Boolean);
      const uniqueNames = new Set(variableNames);
      if (variableNames.length !== uniqueNames.size) {
        this.errors.variables = '存在重复的变量名';
      }

      return Object.keys(this.errors).length === 0 && !this.formError;
    },

    async handleValidate() {
      if (!this.formData.template_content) {
        this.validationResult = {
          valid: false,
          message: '请先输入模板内容',
        };
        return;
      }

      this.validating = true;
      this.validationResult = null;

      try {
        const templateId = this.isEdit ? String(this.templateId) : '0';
        const result = await this.validateTemplate({
          id: templateId,
          templateContent: this.formData.template_content,
        });

        this.validationResult = result;
      } catch (error) {
        console.error('验证失败:', error);
        this.validationResult = {
          valid: false,
          message: error.response?.data?.error || '验证失败',
        };
      } finally {
        this.validating = false;
      }
    },

    handlePreview() {
      this.previewResult = null;
      this.previewError = '';
      this.previewVariables = {};

      this.variableList.forEach((variable) => {
        this.previewVariables[variable.name] = '';
      });

      this.$refs.previewDialog.showModal();
    },

    async executePreview() {
      this.previewing = true;
      this.previewError = '';
      this.previewResult = null;

      try {
        const templateId = this.isEdit ? String(this.templateId) : '0';
        const result = await this.previewTemplate({
          id: templateId,
          variables: this.previewVariables,
        });

        this.previewResult = result;
      } catch (error) {
        console.error('预览失败:', error);
        this.previewError = error.response?.data?.error || '预览失败,请检查变量值';
      } finally {
        this.previewing = false;
      }
    },

    async handleSubmit() {
      if (!this.validateForm()) {
        return;
      }

      this.submitting = true;
      this.formError = '';
      this.formSuccess = '';

      try {
        let response;
        if (this.isEdit) {
          response = await this.updatePromptTemplate({
            id: this.templateId,
            data: this.formData,
          });
          this.formSuccess = '模板更新成功!';
        } else {
          const existingTemplates = this.promptSets.find(
            (set) => String(set.id) === String(this.formData.template_set)
          )?.templates || [];

          const existingTemplate = existingTemplates.find(
            (template) => template.stage_type === this.formData.stage_type
          );

          if (existingTemplate) {
            const stageLabel = this.stageTypes.find(
              (stage) => stage.value === this.formData.stage_type
            )?.label || this.formData.stage_type;

            const confirmed = await this.$confirm(
              `该提示词集中已存在 "${stageLabel}" 类型的模板。

创建新模板将替换现有模板。是否继续？`,
              '模板覆盖确认',
              { tone: 'warning', confirmText: '继续创建' }
            );

            if (!confirmed) {
              this.submitting = false;
              return;
            }
          }

          response = await this.createPromptTemplate(this.formData);
          this.formSuccess = '模板创建成功!';
        }

        this.$emit('saved', response);
      } catch (error) {
        console.error('提交失败:', error);

        if (error.response && error.response.data) {
          const errorData = error.response.data;

          if (typeof errorData === 'object') {
            Object.keys(errorData).forEach((key) => {
              if (key in this.formData) {
                this.errors[key] = Array.isArray(errorData[key])
                  ? errorData[key][0]
                  : errorData[key];
              } else {
                this.formError = Array.isArray(errorData[key])
                  ? errorData[key][0]
                  : errorData[key];
              }
            });
          } else {
            this.formError = errorData.detail || '提交失败,请重试';
          }
        } else {
          this.formError = this.isEdit ? '更新模板失败,请重试' : '创建模板失败,请重试';
        }
      } finally {
        this.submitting = false;
      }
    },
  },
};
</script>

<style scoped>
.prompt-template-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.template-form-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.template-form-toolbar__meta {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.template-form-toolbar__title {
  font-size: 1rem;
  font-weight: 700;
  color: inherit;
}

.template-form-toolbar__hint {
  font-size: 0.82rem;
  color: rgba(100, 116, 139, 0.95);
}

.template-form-toolbar__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .template-form-toolbar__actions {
    width: 100%;
  }
}
</style>
