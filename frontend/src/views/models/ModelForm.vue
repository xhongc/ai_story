<template>
  <div class="model-form">
    <page-card :title="isEdit ? '编辑模型' : '添加模型'">
      <loading-container :loading="loading">
        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- 基本信息 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">模型别名 <span class="text-error">*</span></span>
              </label>
              <input
                v-model="formData.name"
                type="text"
                placeholder="例如: OpenAI GPT-4"
                class="input input-bordered"
                required
              />
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">模型类型 <span class="text-error">*</span></span>
              </label>
              <select
                v-model="formData.provider_type"
                class="select select-bordered"
                required
                :disabled="isEdit"
                @change="handleProviderTypeChange"
              >
                <option value="">请选择类型</option>
                <option value="llm">LLM模型</option>
                <option value="text2image">文生图模型</option>
                <option value="image2video">图生视频模型</option>
              </select>
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">执行器类 <span class="text-error">*</span></span>
              </label>
              <select
                v-model="formData.executor_class"
                class="select select-bordered"
                required
                :disabled="!formData.provider_type || loadingExecutors"
              >
                <option value="">{{ loadingExecutors ? '加载中...' : '请选择执行器' }}</option>
                <option
                  v-for="executor in availableExecutors"
                  :key="executor.value"
                  :value="executor.value"
                >
                  {{ executor.label }}
                </option>
              </select>
              <label class="label">
                <span class="label-text-alt text-base-content/60">
                  选择该模型使用的执行器类
                </span>
              </label>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">API地址 <span class="text-error">*</span></span>
              </label>
              <input
                v-model="formData.api_url"
                type="url"
                placeholder="https://api.openai.com/v1/chat/completions"
                class="input input-bordered"
                required
              />
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">模型名称 <span class="text-error">*</span></span>
              </label>
              <input
                v-model="formData.model_name"
                type="text"
                placeholder="例如: gpt-4-turbo-preview"
                class="input input-bordered"
                required
              />
            </div>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">API密钥 <span class="text-error">*</span></span>
            </label>
            <input
              v-model="formData.api_key"
              type="text"
              placeholder="sk-..."
              class="input input-bordered"
              required
            />
            <label class="label">
              <span class="label-text-alt text-base-content/60">
                密钥将被安全存储,仅显示前8位和后4位
              </span>
            </label>
          </div>

          <!-- LLM专用参数 -->
          <div v-if="formData.provider_type === 'llm'" class="space-y-4">
            <div class="divider">LLM参数配置</div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="form-control">
                <label class="label">
                  <span class="label-text">最大Token数</span>
                </label>
                <input
                  v-model.number="formData.max_tokens"
                  type="number"
                  min="1"
                  max="128000"
                  class="input input-bordered"
                />
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">温度 (0-2)</span>
                </label>
                <input
                  v-model.number="formData.temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  class="input input-bordered"
                />
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">Top P (0-1)</span>
                </label>
                <input
                  v-model.number="formData.top_p"
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  class="input input-bordered"
                />
              </div>
            </div>
          </div>

          <!-- 文生图参数 -->
          <div v-if="formData.provider_type === 'text2image'" class="space-y-4">
            <div class="divider">文生图参数配置</div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="form-control">
                <label class="label">
                  <span class="label-text">默认宽度</span>
                </label>
                <input
                  v-model.number="extraConfig.width"
                  type="number"
                  min="256"
                  max="2048"
                  step="64"
                  class="input input-bordered"
                  placeholder="1024"
                />
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">默认高度</span>
                </label>
                <input
                  v-model.number="extraConfig.height"
                  type="number"
                  min="256"
                  max="2048"
                  step="64"
                  class="input input-bordered"
                  placeholder="1024"
                />
              </div>
            </div>
          </div>

          <!-- 图生视频参数 -->
          <div v-if="formData.provider_type === 'image2video'" class="space-y-4">
            <div class="divider">图生视频参数配置</div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="form-control">
                <label class="label">
                  <span class="label-text">默认FPS</span>
                </label>
                <input
                  v-model.number="extraConfig.fps"
                  type="number"
                  min="12"
                  max="60"
                  class="input input-bordered"
                  placeholder="24"
                />
              </div>

              <div class="form-control">
                <label class="label">
                  <span class="label-text">默认时长(秒)</span>
                </label>
                <input
                  v-model.number="extraConfig.duration"
                  type="number"
                  min="1"
                  max="30"
                  class="input input-bordered"
                  placeholder="5"
                />
              </div>
            </div>
          </div>

          <!-- 通用配置 -->
          <div class="divider">通用配置</div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">优先级</span>
              </label>
              <input
                v-model.number="formData.priority"
                type="number"
                min="0"
                class="input input-bordered"
              />
              <label class="label">
                <span class="label-text-alt text-base-content/60">
                  数值越大优先级越高
                </span>
              </label>
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">每分钟请求限制</span>
              </label>
              <input
                v-model.number="formData.rate_limit_rpm"
                type="number"
                min="1"
                class="input input-bordered"
              />
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">每天请求限制</span>
              </label>
              <input
                v-model.number="formData.rate_limit_rpd"
                type="number"
                min="1"
                class="input input-bordered"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="form-control">
              <label class="label">
                <span class="label-text">超时时间(秒)</span>
              </label>
              <input
                v-model.number="formData.timeout"
                type="number"
                min="1"
                max="600"
                class="input input-bordered"
              />
            </div>

            <div class="form-control">
              <label class="label">
                <span class="label-text">状态</span>
              </label>
              <label class="label cursor-pointer justify-start gap-3">
                <input
                  v-model="formData.is_active"
                  type="checkbox"
                  class="toggle toggle-primary"
                />
                <span class="label-text">{{ formData.is_active ? '已激活' : '未激活' }}</span>
              </label>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-3 pt-4">
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              <span v-if="submitting" class="loading loading-spinner loading-sm"></span>
              {{ submitting ? '保存中...' : '保存' }}
            </button>
            <button
              type="button"
              class="btn btn-ghost"
              @click="handleCancel"
              :disabled="submitting"
            >
              取消
            </button>
          </div>
        </form>
      </loading-container>
    </page-card>
  </div>
</template>

<script>
import { mapActions, mapState } from 'vuex'
import PageCard from '@/components/common/PageCard.vue'
import LoadingContainer from '@/components/common/LoadingContainer.vue'

export default {
  name: 'ModelForm',
  components: {
    PageCard,
    LoadingContainer
  },
  data() {
    return {
      formData: {
        name: '',
        provider_type: '',
        api_url: '',
        api_key: '',
        model_name: '',
        executor_class: '',
        max_tokens: 4096,
        temperature: 0.7,
        top_p: 1.0,
        timeout: 60,
        is_active: true,
        priority: 0,
        rate_limit_rpm: 60,
        rate_limit_rpd: 1000,
        extra_config: {}
      },
      extraConfig: {
        width: 1024,
        height: 1024,
        fps: 24,
        duration: 5
      },
      availableExecutors: [],
      loadingExecutors: false,
      submitting: false
    }
  },
  computed: {
    ...mapState('models', {
      currentProvider: (state) => state.currentProvider,
      loading: (state) => state.loading.currentProvider
    }),
    isEdit() {
      return !!this.$route.params.id
    }
  },
  async created() {
    if (this.isEdit) {
      await this.loadProvider()
    }
  },
  methods: {
    ...mapActions('models', ['fetchProvider', 'createProvider', 'updateProvider']),

    async loadProvider() {
      try {
        const provider = await this.fetchProvider(this.$route.params.id)
        this.formData = { ...this.formData, ...provider }

        // 解析extra_config
        if (provider.extra_config) {
          this.extraConfig = { ...this.extraConfig, ...provider.extra_config }
        }

        // 加载执行器选项
        if (provider.provider_type) {
          await this.loadExecutorChoices(provider.provider_type)
        }
      } catch (error) {
        console.error('加载模型失败:', error)
        alert('加载模型失败')
        this.$router.push({ name: 'ModelList' })
      }
    },

    async handleProviderTypeChange() {
      // 当provider_type改变时，重新加载执行器选项并清空当前选择
      this.formData.executor_class = ''
      if (this.formData.provider_type) {
        await this.loadExecutorChoices(this.formData.provider_type)
      } else {
        this.availableExecutors = []
      }
    },

    async loadExecutorChoices(providerType) {
      this.loadingExecutors = true
      try {
        const { modelProviderApi } = await import('@/api/models')
        const response = await modelProviderApi.getExecutorChoices(providerType)

        // 根据返回格式解析执行器列表
        if (response.executors) {
          // 指定类型的返回格式
          this.availableExecutors = response.executors
        } else if (response[providerType]) {
          // 所有类型的返回格式
          this.availableExecutors = response[providerType]
        } else {
          this.availableExecutors = []
        }

        // 如果只有一个执行器，自动选择
        if (this.availableExecutors.length === 1 && !this.formData.executor_class) {
          this.formData.executor_class = this.availableExecutors[0].value
        }
      } catch (error) {
        console.error('加载执行器选项失败:', error)
        this.availableExecutors = []
      } finally {
        this.loadingExecutors = false
      }
    },

    async handleSubmit() {
      this.submitting = true

      try {
        // 合并extra_config
        const submitData = {
          ...this.formData,
          extra_config: this.extraConfig
        }

        if (this.isEdit) {
          await this.updateProvider({
            id: this.$route.params.id,
            data: submitData
          })
          alert('更新成功')
        } else {
          await this.createProvider(submitData)
          alert('创建成功')
        }

        this.$router.push({ name: 'ModelList' })
      } catch (error) {
        console.error('保存失败:', error)
        const errorMsg = error.response?.data?.error ||
          error.response?.data?.message ||
          Object.values(error.response?.data || {}).flat().join(', ') ||
          '保存失败'
        alert(errorMsg)
      } finally {
        this.submitting = false
      }
    },

    handleCancel() {
      this.$router.push({ name: 'ModelList' })
    }
  }
}
</script>
