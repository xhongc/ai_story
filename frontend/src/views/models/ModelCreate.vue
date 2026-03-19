<template>
  <div class="page-shell model-create">
    <div class="page-header">
      <div class="page-header-main">
        <h1 class="page-title">
          添加模型
        </h1>
        <p class="page-subtitle">
          选择创建方式后，按统一步骤完成模型接入
        </p>
      </div>
      <div class="header-actions">
        <button
          class="secondary-outline-action"
          :disabled="discovering || submittingManual || submittingBatch"
          @click="handleBack"
        >
          返回列表
        </button>
      </div>
    </div>

    <div class="mode-switch-card">
      <button
        class="mode-switch-btn"
        :class="{ active: createMode === 'builtin' }"
        @click="setMode('builtin')"
      >
        内置厂商导入
      </button>
      <button
        class="mode-switch-btn"
        :class="{ active: createMode === 'custom' }"
        @click="setMode('custom')"
      >
        自定义厂商
      </button>
    </div>

    <section class="panel-card mode-guide-card">
      <div class="card-top">
        <div>
          <h2 class="card-title">
            {{ currentModeMeta.title }}
          </h2>
          <p class="card-desc">
            {{ currentModeMeta.description }}
          </p>
        </div>
        <span class="pill">{{ currentModeMeta.pill }}</span>
      </div>

      <div class="mode-guide-steps">
        <div
          v-for="(step, index) in currentFlowSteps"
          :key="step.title"
          class="mode-guide-step"
        >
          <span class="mode-guide-step-index">{{ index + 1 }}</span>
          <div class="mode-guide-step-main">
            <div class="mode-guide-step-title">
              {{ step.title }}
            </div>
            <div class="mode-guide-step-desc">
              {{ step.description }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <section
      v-if="createMode === 'builtin'"
      class="builtin-mode"
    >
      <div class="content-grid">
        <section class="panel-card form-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第一步 · 来源配置
              </h2>
              <p class="card-desc">
                选择内置厂商、模型能力和访问凭证，默认会带出该能力的预设地址
              </p>
            </div>
            <span class="pill">内置厂商</span>
          </div>

          <div class="form-grid">
            <label class="field-block">
              <span class="field-label">模型厂商</span>
              <select
                v-model="vendorForm.vendor"
                class="field-input"
              >
                <option value="">请选择厂商</option>
                <option
                  v-for="vendor in vendors"
                  :key="vendor.key"
                  :value="vendor.key"
                >
                  {{ vendor.label }}
                </option>
              </select>
            </label>

            <label class="field-block">
              <span class="field-label">模型能力</span>
              <select
                v-model="vendorForm.capability"
                class="field-input"
                :disabled="!availableCapabilities.length"
              >
                <option
                  v-for="capability in availableCapabilities"
                  :key="capability.key"
                  :value="capability.key"
                >
                  {{ getProviderTypeLabel(capability.provider_type) }}
                </option>
              </select>
            </label>

            <label
              v-if="selectedCapability"
              class="field-block field-block-wide"
            >
              <span class="field-label">API 地址</span>
              <input
                v-model.trim="vendorForm.api_url"
                type="url"
                class="field-input"
                :placeholder="getApiUrlPlaceholder()"
              >
              <span class="field-hint">默认已带出预设地址，可按当前模型能力改成你的自定义网关地址</span>
            </label>

            <label class="field-block field-block-wide">
              <span class="field-label">API Key</span>
              <input
                v-model.trim="vendorForm.api_key"
                type="password"
                class="field-input"
                placeholder="请输入该厂商 API Key"
              >
            </label>
          </div>

          <div class="discover-actions mt-2">
            <button
              class="primary-action"
              :disabled="discovering || !canDiscover"
              @click="handleDiscover"
            >
              {{ discovering ? '拉取中...' : '拉取模型列表' }}
            </button>
          </div>
        </section>

        <section class="panel-card setting-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第二步 · 默认配置
              </h2>
              <p class="card-desc">
                这些默认参数会应用到本次批量创建的全部模型
              </p>
            </div>
          </div>

          <div class="form-grid compact-grid">
            <label class="field-block">
              <span class="field-label">超时(秒)</span>
              <input
                v-model.number="vendorForm.timeout"
                type="number"
                min="1"
                max="600"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">最大 Token</span>
              <input
                v-model.number="vendorForm.max_tokens"
                type="number"
                min="1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">Temperature</span>
              <input
                v-model.number="vendorForm.temperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">Top P</span>
              <input
                v-model.number="vendorForm.top_p"
                type="number"
                min="0"
                max="1"
                step="0.1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">每分钟限制</span>
              <input
                v-model.number="vendorForm.rate_limit_rpm"
                type="number"
                min="1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">每天限制</span>
              <input
                v-model.number="vendorForm.rate_limit_rpd"
                type="number"
                min="1"
                class="field-input"
              >
            </label>
          </div>

          <label class="toggle-row">
            <input
              v-model="vendorForm.is_active"
              type="checkbox"
            >
            <span>{{ vendorForm.is_active ? '创建后默认激活' : '创建后默认停用' }}</span>
          </label>
        </section>
      </div>

      <section class="panel-card result-card">
        <div class="card-top">
          <div>
            <h2 class="card-title">
              可创建模型
            </h2>
            <p class="card-desc">
              已选 {{ selectedModelNames.length }} / {{ visibleModels.length }} 个模型
            </p>
          </div>
          <div class="result-actions result-actions-wide">
            <div
              v-if="discoveredModels.length"
              class="status-filters"
            >
              <button
                v-for="filter in classificationFilters"
                :key="filter.value"
                class="status-filter-btn"
                :class="{ active: modelFilterMode === filter.value }"
                @click="setModelFilterMode(filter.value)"
              >
                {{ filter.label }}
                <span class="filter-count">{{ filter.count }}</span>
              </button>
            </div>
            <button
              class="ghost-action"
              :disabled="!visibleModels.length"
              @click="selectAll"
            >
              全选
            </button>
            <button
              class="ghost-action"
              :disabled="!selectedModelNames.length"
              @click="clearSelection"
            >
              清空
            </button>
            <button
              class="primary-action"
              :disabled="submittingBatch || !selectedModelNames.length || !vendorForm.vendor || !vendorForm.api_key"
              @click="handleBatchCreate"
            >
              {{ submittingBatch ? '创建中...' : '批量创建选中模型' }}
            </button>
          </div>
        </div>

        <div
          v-if="!discoveredModels.length"
          class="empty-state"
        >
          <div class="empty-hero">
            等待拉取可创建模型
          </div>
          <p class="empty-hint">
            先完成第一步来源配置，再拉取该能力下可批量导入的模型列表
          </p>
        </div>

        <div
          v-else
          class="model-grid"
        >
          <label
            v-for="model in visibleModels"
            :key="model.id"
            class="model-option"
            :class="{ selected: selectedModelNames.includes(model.id) }"
          >
            <input
              v-model="selectedModelNames"
              type="checkbox"
              :value="model.id"
            >
            <div class="model-option-main">
              <div class="model-option-title">
                {{ model.name || model.id }}
                <span
                  v-if="model.is_capability_match || model.classified_capability_label"
                  class="recommend-badge"
                >
                  {{ model.classified_capability_label || selectedCapabilityFilterLabel }}
                </span>
              </div>
              <div class="model-option-desc">
                {{ model.id }}
              </div>
              <div
                v-if="model.classified_capability_label"
                class="model-option-meta"
              >
                分类：{{ model.classified_capability_label }}
              </div>
            </div>
          </label>
        </div>
      </section>

      <section
        v-if="submitBatchResult"
        class="panel-card summary-card"
      >
        <div class="card-top">
          <div>
            <h2 class="card-title">
              创建结果
            </h2>
            <p class="card-desc">
              已创建 {{ submitBatchResult.created_count }} 个，跳过 {{ submitBatchResult.skipped_count }} 个
            </p>
          </div>
        </div>

        <div class="result-summary-grid">
          <div class="summary-pane">
            <div class="summary-pane-title">
              新建成功
            </div>
            <div
              v-if="submitBatchResult.created && submitBatchResult.created.length"
              class="tag-list"
            >
              <span
                v-for="item in submitBatchResult.created"
                :key="item.id"
                class="result-tag success"
              >
                {{ item.model_name }}
              </span>
            </div>
            <p
              v-else
              class="empty-inline"
            >
              本次没有新增模型
            </p>
          </div>

          <div class="summary-pane">
            <div class="summary-pane-title">
              已跳过
            </div>
            <div
              v-if="submitBatchResult.skipped && submitBatchResult.skipped.length"
              class="tag-list"
            >
              <span
                v-for="item in submitBatchResult.skipped"
                :key="`${item.model_name}-${item.id || item.name}`"
                class="result-tag muted-tag"
              >
                {{ item.model_name }}
              </span>
            </div>
            <p
              v-else
              class="empty-inline"
            >
              没有跳过项
            </p>
          </div>
        </div>
      </section>
    </section>

    <section
      v-else
      class="custom-mode"
    >
      <form
        class="form-layout"
        @submit.prevent="handleManualSubmit"
      >
        <section class="panel-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第一步 · 来源配置
              </h2>
              <p class="card-desc">
                填写自定义厂商模型的基础信息、能力类型与访问配置
              </p>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-block">
              <span class="field-label">模型别名 <em>*</em></span>
              <input
                v-model="manualFormData.name"
                type="text"
                placeholder="例如: My Gateway GPT-4"
                class="field-input"
                required
              >
            </label>

            <label class="field-block">
              <span class="field-label">模型类型 <em>*</em></span>
              <select
                v-model="manualFormData.provider_type"
                class="field-input"
                required
                @change="handleProviderTypeChange"
              >
                <option value="">请选择类型</option>
                <option value="llm">LLM模型</option>
                <option value="text2image">文生图模型</option>
                <option value="image2video">图生视频模型</option>
                <option value="image_edit">图片编辑模型</option>
              </select>
            </label>

            <label class="field-block">
              <span class="field-label">执行器类 <em>*</em></span>
              <select
                v-model="manualFormData.executor_class"
                class="field-input"
                required
                :disabled="!manualFormData.provider_type || loadingExecutors"
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
              <span class="field-hint">选择该模型使用的执行器类</span>
            </label>

            <label class="field-block field-block-wide">
              <span class="field-label">API地址 <em>*</em></span>
              <input
                v-model="manualFormData.api_url"
                type="url"
                placeholder="https://example.com/v1/chat/completions"
                class="field-input"
                required
              >
            </label>

            <label class="field-block">
              <span class="field-label">模型名称 <em>*</em></span>
              <input
                v-model="manualFormData.model_name"
                type="text"
                placeholder="例如: my-model"
                class="field-input"
                required
              >
            </label>

            <label class="field-block">
              <span class="field-label">API密钥 <em>*</em></span>
              <input
                v-model="manualFormData.api_key"
                type="text"
                placeholder="sk-..."
                class="field-input"
                required
              >
            </label>
          </div>
        </section>

        <section
          v-if="manualFormData.provider_type === 'llm'"
          class="panel-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                LLM 参数配置
              </h2>
              <p class="card-desc">
                控制文本生成的采样和长度
              </p>
            </div>
          </div>

          <div class="form-grid form-grid-3">
            <label class="field-block">
              <span class="field-label">最大Token数</span>
              <input
                v-model.number="manualFormData.max_tokens"
                type="number"
                min="1"
                max="128000"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">温度 (0-2)</span>
              <input
                v-model.number="manualFormData.temperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">Top P (0-1)</span>
              <input
                v-model.number="manualFormData.top_p"
                type="number"
                min="0"
                max="1"
                step="0.1"
                class="field-input"
              >
            </label>
          </div>
        </section>

        <section
          v-if="manualFormData.provider_type === 'text2image'"
          class="panel-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第二步 · 能力参数
              </h2>
              <p class="card-desc">
                设置默认输出尺寸
              </p>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-block">
              <span class="field-label">默认宽度</span>
              <input
                v-model.number="manualExtraConfig.width"
                type="number"
                min="256"
                max="10240"
                step="32"
                class="field-input"
                placeholder="1024"
              >
            </label>
            <label class="field-block">
              <span class="field-label">默认高度</span>
              <input
                v-model.number="manualExtraConfig.height"
                type="number"
                min="256"
                max="10240"
                step="32"
                class="field-input"
                placeholder="1024"
              >
            </label>
          </div>
        </section>

        <section
          v-if="manualFormData.provider_type === 'image2video'"
          class="panel-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第二步 · 能力参数
              </h2>
              <p class="card-desc">
                设置默认帧率与时长
              </p>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-block">
              <span class="field-label">默认FPS</span>
              <input
                v-model.number="manualExtraConfig.fps"
                type="number"
                min="12"
                max="60"
                class="field-input"
                placeholder="24"
              >
            </label>
            <label class="field-block">
              <span class="field-label">默认时长(秒)</span>
              <input
                v-model.number="manualExtraConfig.duration"
                type="number"
                min="1"
                max="30"
                class="field-input"
                placeholder="5"
              >
            </label>
          </div>
        </section>

        <section
          v-if="manualFormData.provider_type === 'image_edit'"
          class="panel-card"
        >
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第二步 · 能力参数
              </h2>
              <p class="card-desc">
                设置默认画布尺寸与重绘强度
              </p>
            </div>
          </div>

          <div class="form-grid form-grid-3">
            <label class="field-block">
              <span class="field-label">默认宽度</span>
              <input
                v-model.number="manualExtraConfig.width"
                type="number"
                min="256"
                max="10240"
                step="32"
                class="field-input"
                placeholder="1024"
              >
            </label>
            <label class="field-block">
              <span class="field-label">默认高度</span>
              <input
                v-model.number="manualExtraConfig.height"
                type="number"
                min="256"
                max="10240"
                step="32"
                class="field-input"
                placeholder="1024"
              >
            </label>
            <label class="field-block">
              <span class="field-label">默认重绘强度</span>
              <input
                v-model.number="manualExtraConfig.strength"
                type="number"
                min="0"
                max="1"
                step="0.05"
                class="field-input"
                placeholder="0.35"
              >
            </label>
          </div>
        </section>

        <section class="panel-card">
          <div class="card-top">
            <div>
              <h2 class="card-title">
                第三步 · 默认配置
              </h2>
              <p class="card-desc">
                设置优先级、限流、超时和启用状态
              </p>
            </div>
          </div>

          <div class="form-grid form-grid-3">
            <label class="field-block">
              <span class="field-label">优先级</span>
              <input
                v-model.number="manualFormData.priority"
                type="number"
                min="0"
                class="field-input"
              >
              <span class="field-hint">数值越大优先级越高</span>
            </label>
            <label class="field-block">
              <span class="field-label">每分钟请求限制</span>
              <input
                v-model.number="manualFormData.rate_limit_rpm"
                type="number"
                min="1"
                class="field-input"
              >
            </label>
            <label class="field-block">
              <span class="field-label">每天请求限制</span>
              <input
                v-model.number="manualFormData.rate_limit_rpd"
                type="number"
                min="1"
                class="field-input"
              >
            </label>
          </div>

          <div class="form-grid utility-grid">
            <label class="field-block">
              <span class="field-label">超时时间(秒)</span>
              <input
                v-model.number="manualFormData.timeout"
                type="number"
                min="1"
                max="600"
                class="field-input"
              >
            </label>

            <label class="toggle-card">
              <span class="field-label">状态</span>
              <span class="toggle-inner">
                <input
                  v-model="manualFormData.is_active"
                  type="checkbox"
                >
                <span class="toggle-text">{{ manualFormData.is_active ? '已激活' : '未激活' }}</span>
              </span>
            </label>
          </div>
        </section>

        <div class="form-actions">
          <button
            type="submit"
            class="primary-action"
            :disabled="submittingManual"
          >
            {{ submittingManual ? '创建中...' : '创建模型' }}
          </button>
          <button
            type="button"
            class="secondary-outline-action"
            :disabled="submittingManual"
            @click="handleBack"
          >
            取消
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<script>
import { mapActions } from 'vuex'
import { modelProviderApi } from '@/api/models'

const VENDOR_API_KEY_STORAGE_KEY = 'model_vendor_api_keys'

export default {
  name: 'ModelCreate',
  data() {
    return {
      createMode: 'builtin',
      vendors: [],
      vendorForm: {
        vendor: '',
        capability: 'llm',
        api_key: '',
        api_url: '',
        is_active: true,
        timeout: 60,
        max_tokens: 40960,
        temperature: 0.7,
        top_p: 1,
        rate_limit_rpm: 60,
        rate_limit_rpd: 1000,
        priority: 0
      },
      discoveredModels: [],
      selectedModelNames: [],
      modelFilterMode: 'all',
      discovering: false,
      submittingBatch: false,
      submitBatchResult: null,
      manualFormData: {
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
      manualExtraConfig: {
        width: 1024,
        height: 1024,
        fps: 24,
        duration: 5,
        strength: 0.35
      },
      availableExecutors: [],
      loadingExecutors: false,
      submittingManual: false
    }
  },
  computed: {
    selectedVendor() {
      return this.vendors.find((item) => item.key === this.vendorForm.vendor) || null
    },
    availableCapabilities() {
      return this.selectedVendor?.capabilities || []
    },
    selectedCapability() {
      return this.availableCapabilities.find((item) => item.key === this.vendorForm.capability) || null
    },
    currentModeMeta() {
      if (this.createMode === 'builtin') {
        return {
          title: '内置厂商导入',
          description: '适合已经接入主流厂商的场景，只需填写 API Key 和可选网关地址，即可批量导入模型。',
          pill: '批量导入'
        }
      }
      return {
        title: '自定义厂商创建',
        description: '适合私有网关、代理服务或未内置的模型平台，按能力类型手动创建单个模型。',
        pill: '手动创建'
      }
    },
    currentFlowSteps() {
      if (this.createMode === 'builtin') {
        return [
          { title: '配置来源', description: '选择厂商、能力、API 地址与 API Key' },
          { title: '设置默认参数', description: '统一设置超时、Token 与限流配置' },
          { title: '拉取并创建模型', description: '勾选推荐或全部模型后批量创建' }
        ]
      }
      return [
        { title: '填写基础信息', description: '配置别名、能力类型、执行器和访问地址' },
        { title: '补充能力参数', description: '按文生图、图生视频或图片编辑补充默认参数' },
        { title: '完成创建', description: '设置通用配置后直接创建单个模型' }
      ]
    },
    selectedCapabilityFilterLabel() {
      if (!this.selectedCapability) {
        return '能力匹配模型'
      }
      return this.getProviderTypeLabel(this.selectedCapability.provider_type)
    },
    canDiscover() {
      return Boolean(this.vendorForm.vendor && this.vendorForm.capability && this.vendorForm.api_key)
    },
    classificationFilters() {
      const counts = this.discoveredModels.reduce((result, item) => {
        const key = item.classified_capability || 'unclassified'
        result[key] = (result[key] || 0) + 1
        return result
      }, {})
      const filters = []
      const preferredKey = this.selectedCapability?.provider_type || this.vendorForm.capability
      if (preferredKey && counts[preferredKey]) {
        filters.push({
          value: preferredKey,
          label: this.getProviderTypeLabel(preferredKey),
          count: counts[preferredKey]
        })
      }
      ['llm', 'vlm', 'text2image', 'image2video', 'image_edit'].forEach((key) => {
        if (!counts[key] || key === preferredKey) {
          return
        }
        filters.push({
          value: key,
          label: this.getProviderTypeLabel(key),
          count: counts[key]
        })
      })
      if (counts.unclassified) {
        filters.push({
          value: 'unclassified',
          label: '未分类',
          count: counts.unclassified
        })
      }
      filters.push({
        value: 'all',
        label: '全部模型',
        count: this.discoveredModels.length
      })
      return filters
    },
    visibleModels() {
      if (this.modelFilterMode === 'all') {
        return this.discoveredModels
      }
      if (this.modelFilterMode === 'unclassified') {
        return this.discoveredModels.filter((item) => !item.classified_capability)
      }
      return this.discoveredModels.filter((item) => item.classified_capability === this.modelFilterMode)
    }
  },
  watch: {
    '$route.query.mode': {
      immediate: true,
      handler(value) {
        if (value === 'custom' || value === 'builtin') {
          this.createMode = value
          return
        }
        this.createMode = this.$route.name === 'model-batch-create' ? 'builtin' : 'custom'
      }
    },
    'vendorForm.vendor'(value) {
      const vendor = this.vendors.find((item) => item.key === value)
      const capabilities = vendor?.capabilities || []
      if (!capabilities.length) {
        this.vendorForm.capability = 'llm'
        this.vendorForm.api_key = this.getStoredVendorApiKey(value)
        return
      }
      if (!capabilities.some((item) => item.key === this.vendorForm.capability)) {
        this.vendorForm.capability = capabilities[0].key
      }
      this.discoveredModels = []
      this.selectedModelNames = []
      this.submitBatchResult = null
      this.vendorForm.api_key = this.getStoredVendorApiKey(value)
      this.syncVendorApiUrl()
    },
    'vendorForm.capability'() {
      this.discoveredModels = []
      this.selectedModelNames = []
      this.submitBatchResult = null
      this.syncVendorApiUrl()
    }
  },
  async created() {
    await this.loadVendors()
  },
  methods: {
    ...mapActions('models', ['createProvider']),

    setMode(mode) {
      this.createMode = mode
      this.$router.replace({
        name: this.$route.name,
        query: {
          ...this.$route.query,
          mode
        }
      })
    },

    handleBack() {
      this.$router.push({ name: 'ModelList' })
    },

    getProviderTypeLabel(type) {
      const labels = {
        llm: '语言模型',
        vlm: '视觉语言模型',
        text2image: '文生图',
        image2video: '图生视频',
        image_edit: '图片编辑'
      }
      return labels[type] || type
    },

    syncVendorApiUrl() {
      const nextApiUrl = this.selectedCapability?.api_url || ''
      if (!nextApiUrl) {
        this.vendorForm.api_url = ''
        return
      }
      if (!this.vendorForm.api_url || this.vendorForm.api_url !== nextApiUrl) {
        this.vendorForm.api_url = nextApiUrl
      }
    },

    getApiUrlPlaceholder() {
      return this.selectedCapability?.api_url || '请输入完整的 API 地址'
    },

    getVendorApiKeyStore() {
      try {
        const rawValue = localStorage.getItem(VENDOR_API_KEY_STORAGE_KEY)
        return rawValue ? JSON.parse(rawValue) : {}
      } catch (error) {
        console.warn('读取厂商 API Key 缓存失败:', error)
        return {}
      }
    },

    getStoredVendorApiKey(vendor) {
      if (!vendor) {
        return ''
      }
      const store = this.getVendorApiKeyStore()
      return store[vendor] || ''
    },

    persistVendorApiKey(vendor, apiKey) {
      if (!vendor) {
        return
      }
      const store = this.getVendorApiKeyStore()
      const nextApiKey = (apiKey || '').trim()
      if (nextApiKey) {
        store[vendor] = nextApiKey
      } else {
        delete store[vendor]
      }
      localStorage.setItem(VENDOR_API_KEY_STORAGE_KEY, JSON.stringify(store))
    },

    async loadVendors() {
      try {
        const response = await modelProviderApi.getBuiltinVendors()
        this.vendors = response.results || []
      } catch (error) {
        console.error('加载内置厂商失败:', error)
        await this.$alert('加载内置厂商失败', '加载失败', { tone: 'error' })
      }
    },

    async handleDiscover() {
      if (!this.canDiscover) {
        await this.$alert('请先选择厂商并填写 API Key', '提示', { tone: 'warning' })
        return
      }

      this.discovering = true
      this.submitBatchResult = null
      try {
        const response = await modelProviderApi.discoverVendorModels({
          vendor: this.vendorForm.vendor,
          capability: this.vendorForm.capability,
          api_key: this.vendorForm.api_key,
          api_url: this.vendorForm.api_url
        })
        this.persistVendorApiKey(this.vendorForm.vendor, this.vendorForm.api_key)
        this.discoveredModels = response.models || []
        const preferredMode = this.selectedCapability?.provider_type || this.vendorForm.capability
        this.modelFilterMode = this.discoveredModels.some((item) => item.classified_capability === preferredMode)
          ? preferredMode
          : 'all'
        const defaultModels = this.modelFilterMode === 'all'
          ? this.discoveredModels
          : this.discoveredModels.filter((item) => item.classified_capability === this.modelFilterMode)
        this.selectedModelNames = defaultModels.map((item) => item.id)
        if (!this.discoveredModels.length) {
          await this.$alert('当前厂商未返回可导入模型', '拉取完成', { tone: 'warning' })
        }
      } catch (error) {
        console.error('拉取模型列表失败:', error)
        await this.$alert(
          error.response?.data?.error || '拉取模型列表失败',
          '拉取失败',
          { tone: 'error' }
        )
      } finally {
        this.discovering = false
      }
    },

    setModelFilterMode(mode) {
      this.modelFilterMode = mode
      this.selectedModelNames = this.visibleModels.map((item) => item.id)
    },

    selectAll() {
      this.selectedModelNames = this.visibleModels.map((item) => item.id)
    },

    clearSelection() {
      this.selectedModelNames = []
    },

    async handleBatchCreate() {
      if (!this.selectedModelNames.length) {
        await this.$alert('请至少选择一个模型', '提示', { tone: 'warning' })
        return
      }

      this.submittingBatch = true
      try {
        const response = await modelProviderApi.batchCreateVendorModels({
          vendor: this.vendorForm.vendor,
          capability: this.vendorForm.capability,
          api_key: this.vendorForm.api_key,
          api_url: this.vendorForm.api_url,
          model_names: this.selectedModelNames,
          is_active: this.vendorForm.is_active,
          timeout: this.vendorForm.timeout,
          max_tokens: this.vendorForm.max_tokens,
          temperature: this.vendorForm.temperature,
          top_p: this.vendorForm.top_p,
          rate_limit_rpm: this.vendorForm.rate_limit_rpm,
          rate_limit_rpd: this.vendorForm.rate_limit_rpd,
          priority: this.vendorForm.priority
        })
        this.persistVendorApiKey(this.vendorForm.vendor, this.vendorForm.api_key)
        this.submitBatchResult = response
        await this.$alert(
          `创建完成：新增 ${response.created_count} 个，跳过 ${response.skipped_count} 个`,
          '操作完成',
          { tone: 'success' }
        )
      } catch (error) {
        console.error('批量创建模型失败:', error)
        await this.$alert(
          error.response?.data?.error || '批量创建模型失败',
          '创建失败',
          { tone: 'error' }
        )
      } finally {
        this.submittingBatch = false
      }
    },

    async handleProviderTypeChange() {
      this.manualFormData.executor_class = ''
      if (this.manualFormData.provider_type) {
        await this.loadExecutorChoices(this.manualFormData.provider_type)
      } else {
        this.availableExecutors = []
      }
    },

    async loadExecutorChoices(providerType) {
      this.loadingExecutors = true
      try {
        const response = await modelProviderApi.getExecutorChoices(providerType)
        if (response.executors) {
          this.availableExecutors = response.executors
        } else if (response[providerType]) {
          this.availableExecutors = response[providerType]
        } else {
          this.availableExecutors = []
        }
        if (this.availableExecutors.length === 1 && !this.manualFormData.executor_class) {
          this.manualFormData.executor_class = this.availableExecutors[0].value
        }
      } catch (error) {
        console.error('加载执行器选项失败:', error)
        this.availableExecutors = []
      } finally {
        this.loadingExecutors = false
      }
    },

    async handleManualSubmit() {
      this.submittingManual = true
      try {
        const submitData = {
          ...this.manualFormData,
          extra_config: {
            ...this.manualExtraConfig,
            vendor: 'custom',
            vendor_label: '自定义厂商',
            vendor_source: 'manual'
          }
        }
        await this.createProvider(submitData)
        await this.$alert('创建成功', '操作完成', { tone: 'success' })
        this.$router.push({ name: 'ModelList' })
      } catch (error) {
        console.error('保存失败:', error)
        const errorMsg = error.response?.data?.error ||
          error.response?.data?.message ||
          Object.values(error.response?.data || {}).flat().join(', ') ||
          '保存失败'
        await this.$alert(errorMsg, '保存失败', { tone: 'error' })
      } finally {
        this.submittingManual = false
      }
    }
  }
}
</script>

<style scoped>
.page-shell {
  min-height: 100vh;
  padding: 2.5rem 3.5rem 3rem;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.page-header-main {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.layout-shell.theme-dark .page-title {
  color: #e2e8f0;
}

.page-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0;
}

.layout-shell.theme-dark .page-subtitle {
  color: #94a3b8;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.mode-switch-card {
  display: inline-flex;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  margin-bottom: 1.5rem;
}

.layout-shell.theme-dark .mode-switch-card {
  background: rgba(15, 23, 42, 0.88);
  border-color: rgba(148, 163, 184, 0.18);
}

.mode-switch-btn {
  padding: 0.72rem 1.2rem;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .mode-switch-btn {
  color: #cbd5e1;
}

.mode-switch-btn.active {
  background: rgba(20, 184, 166, 0.16);
  border-color: rgba(20, 184, 166, 0.5);
  color: #0f172a;
}

.layout-shell.theme-dark .mode-switch-btn.active {
  background: rgba(94, 234, 212, 0.2);
  border-color: rgba(94, 234, 212, 0.5);
  color: #e2e8f0;
}

.mode-guide-card {
  margin-bottom: 1.25rem;
}

.mode-guide-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.mode-guide-step {
  display: flex;
  gap: 0.8rem;
  align-items: flex-start;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  background: rgba(148, 163, 184, 0.1);
}

.layout-shell.theme-dark .mode-guide-step {
  background: rgba(30, 41, 59, 0.6);
}

.mode-guide-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 700;
}

.layout-shell.theme-dark .mode-guide-step-index {
  background: rgba(94, 234, 212, 0.2);
  color: #e2e8f0;
}

.mode-guide-step-title {
  color: #0f172a;
  font-weight: 600;
}

.layout-shell.theme-dark .mode-guide-step-title {
  color: #e2e8f0;
}

.mode-guide-step-desc {
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.5;
}

.layout-shell.theme-dark .mode-guide-step-desc {
  color: #94a3b8;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.form-layout {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.panel-card {
  background: linear-gradient(90deg, rgba(20, 184, 166, 0.7) 0%, rgba(14, 165, 233, 0.7) 100%) 0 0 / 0 3px no-repeat,
    rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 1.35rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
}

.layout-shell.theme-dark .panel-card {
  background: linear-gradient(90deg, rgba(94, 234, 212, 0.5) 0%, rgba(56, 189, 248, 0.5) 100%) 0 0 / 0 3px no-repeat,
    rgba(15, 23, 42, 0.92);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 32px rgba(2, 6, 23, 0.55);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.card-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .card-title {
  color: #e2e8f0;
}

.card-desc {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.layout-shell.theme-dark .card-desc {
  color: #94a3b8;
}

.pill {
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
}

.layout-shell.theme-dark .pill {
  background: rgba(94, 234, 212, 0.22);
  color: #e2e8f0;
}

.form-grid,
.vendor-summary,
.result-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.compact-grid,
.form-grid-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.utility-grid {
  margin-top: 1rem;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.field-block-wide,
.summary-item-wide {
  grid-column: 1 / -1;
}

.field-label,
.summary-label,
.summary-pane-title {
  font-size: 0.82rem;
  color: #64748b;
}

.field-label em {
  font-style: normal;
  color: #ef4444;
}

.layout-shell.theme-dark .field-label,
.layout-shell.theme-dark .summary-label,
.layout-shell.theme-dark .summary-pane-title {
  color: #94a3b8;
}

.field-input {
  width: 100%;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
  outline: none;
  transition: all 0.2s ease;
}

.layout-shell.theme-dark .field-input {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.22);
  color: #e2e8f0;
}

.field-input:focus {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}

.field-hint {
  font-size: 0.78rem;
  color: #94a3b8;
}

.summary-item,
.summary-pane,
.toggle-card {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 14px;
  padding: 0.85rem 1rem;
}

.layout-shell.theme-dark .summary-item,
.layout-shell.theme-dark .summary-pane,
.layout-shell.theme-dark .toggle-card {
  background: rgba(30, 41, 59, 0.6);
}

.summary-value {
  color: #0f172a;
  font-weight: 600;
}

.layout-shell.theme-dark .summary-value {
  color: #e2e8f0;
}

.summary-url {
  word-break: break-all;
}

.vendor-summary-single {
  grid-template-columns: 1fr;
}

.discover-actions,
.result-actions,
.form-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: center;
}

.result-actions-wide {
  justify-content: flex-end;
}

.status-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-right: auto;
}

.status-filter-btn,
.mode-switch-btn,
.primary-action,
.secondary-outline-action,
.ghost-action {
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-filter-btn {
  padding: 0.5rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 500;
}

.layout-shell.theme-dark .status-filter-btn {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(148, 163, 184, 0.25);
  color: #cbd5e1;
}

.status-filter-btn.active {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  border-color: rgba(20, 184, 166, 0.5);
}

.layout-shell.theme-dark .status-filter-btn.active {
  background: rgba(94, 234, 212, 0.2);
  color: #e2e8f0;
  border-color: rgba(94, 234, 212, 0.5);
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.85rem;
}

.model-option {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.72);
}

.layout-shell.theme-dark .model-option {
  background: rgba(15, 23, 42, 0.72);
  border-color: rgba(148, 163, 184, 0.18);
}

.model-option.selected {
  border-color: rgba(20, 184, 166, 0.45);
  box-shadow: 0 10px 24px rgba(20, 184, 166, 0.12);
  transform: translateY(-2px);
}

.model-option-main {
  min-width: 0;
}

.model-option-title {
  color: #0f172a;
  font-weight: 600;
  word-break: break-word;
  display: flex;
  gap: 0.45rem;
  align-items: center;
  flex-wrap: wrap;
}

.layout-shell.theme-dark .model-option-title {
  color: #e2e8f0;
}

.model-option-desc {
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.82rem;
  word-break: break-all;
}

.model-option-meta {
  margin-top: 0.35rem;
  color: #94a3b8;
  font-size: 0.76rem;
}

.layout-shell.theme-dark .model-option-desc {
  color: #94a3b8;
}

.layout-shell.theme-dark .model-option-meta {
  color: #94a3b8;
}

.recommend-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  background: rgba(20, 184, 166, 0.16);
  color: #0f766e;
}

.filter-count {
  margin-left: 0.35rem;
  opacity: 0.8;
  font-size: 0.78rem;
}

.layout-shell.theme-dark .recommend-badge {
  background: rgba(94, 234, 212, 0.2);
  color: #99f6e4;
}

.primary-action,
.secondary-outline-action,
.ghost-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.72rem 1.35rem;
  border-radius: 999px;
  font-size: 0.92rem;
}

.primary-action {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #0f172a;
}

.secondary-outline-action,
.ghost-action {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.85);
  color: #334155;
}

.layout-shell.theme-dark .primary-action,
.layout-shell.theme-dark .secondary-outline-action,
.layout-shell.theme-dark .ghost-action {
  background: rgba(15, 23, 42, 0.9);
  color: #e2e8f0;
  border-color: rgba(148, 163, 184, 0.24);
}

.primary-action:hover,
.secondary-outline-action:hover,
.ghost-action:hover,
.status-filter-btn:hover,
.mode-switch-btn:hover {
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.18);
  transform: translateY(-1px);
}

.toggle-row,
.toggle-inner {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  color: #475569;
}

.layout-shell.theme-dark .toggle-row,
.layout-shell.theme-dark .toggle-inner {
  color: #cbd5e1;
}

.result-card,
.summary-card {
  margin-top: 1.25rem;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.result-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.38rem 0.7rem;
  border-radius: 999px;
  font-size: 0.82rem;
}

.result-tag.success {
  background: rgba(16, 185, 129, 0.14);
  color: #047857;
}

.result-tag.muted-tag {
  background: rgba(148, 163, 184, 0.16);
  color: #475569;
}

.layout-shell.theme-dark .result-tag.success {
  color: #86efac;
}

.layout-shell.theme-dark .result-tag.muted-tag {
  color: #cbd5e1;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
}

.empty-hero {
  font-size: 1.2rem;
  font-weight: 600;
  color: #0f172a;
}

.layout-shell.theme-dark .empty-hero {
  color: #e2e8f0;
}

.empty-hint,
.empty-inline {
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .mode-guide-steps,
  .content-grid,
  .compact-grid,
  .form-grid-3 {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-shell {
    padding: 2rem 1.5rem;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .mode-switch-card,
  .header-actions,
  .discover-actions,
  .result-actions,
  .form-actions {
    width: 100%;
  }

  .mode-switch-card {
    display: flex;
    flex-direction: column;
    border-radius: 18px;
  }

  .mode-switch-btn,
  .primary-action,
  .secondary-outline-action,
  .ghost-action {
    width: 100%;
  }

  .form-grid,
  .vendor-summary,
  .result-summary-grid,
  .utility-grid {
    grid-template-columns: 1fr;
  }

  .status-filters {
    width: 100%;
    margin-right: 0;
  }
}
</style>
