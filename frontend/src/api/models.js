/**
 * 模型管理 API 服务层
 * 职责: 封装所有模型相关的 API 请求
 * 遵循单一职责原则(SRP)
 */

import apiClient from '@/services/apiClient'

/**
 * 模型提供商相关 API
 */
export const modelProviderApi = {
  /**
   * 获取模型提供商列表
   * @param {Object} params - 查询参数
   * @param {string} params.provider_type - 提供商类型 (llm/text2image/image2video/image_edit)
   * @param {boolean} params.is_active - 是否激活
   * @param {string} params.search - 搜索关键词
   * @param {string} params.ordering - 排序字段
   * @returns {Promise}
   */
  getProviders(params = {}) {
    return apiClient.get('/models/providers/', { params })
  },

  /**
   * 获取模型提供商详情
   * @param {string} id - 提供商ID
   * @returns {Promise}
   */
  getProvider(id) {
    return apiClient.get(`/models/providers/${id}/`)
  },

  /**
   * 创建模型提供商
   * @param {Object} data - 提供商数据
   * @returns {Promise}
   */
  createProvider(data) {
    return apiClient.post('/models/providers/', data)
  },

  /**
   * 更新模型提供商
   * @param {string} id - 提供商ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  updateProvider(id, data) {
    return apiClient.put(`/models/providers/${id}/`, data)
  },

  /**
   * 部分更新模型提供商
   * @param {string} id - 提供商ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  patchProvider(id, data) {
    return apiClient.patch(`/models/providers/${id}/`, data)
  },

  /**
   * 删除模型提供商
   * @param {string} id - 提供商ID
   * @returns {Promise}
   */
  deleteProvider(id) {
    return apiClient.delete(`/models/providers/${id}/`)
  },

  /**
   * 切换模型提供商激活状态
   * @param {string} id - 提供商ID
   * @returns {Promise}
   */
  toggleProviderStatus(id) {
    return apiClient.post(`/models/providers/${id}/toggle_status/`)
  },

  /**
   * 获取模型提供商统计信息
   * @param {string} id - 提供商ID
   * @returns {Promise}
   */
  getProviderStatistics(id) {
    return apiClient.get(`/models/providers/${id}/statistics/`)
  },

  /**
   * 测试模型提供商连接
   * @param {string} id - 提供商ID
   * @param {string|Object} payload - 测试提示词或测试参数对象
   * @returns {Promise}
   */
  testProviderConnection(id, payload = 'Hello, this is a test.') {
    const requestBody = typeof payload === 'string'
      ? { test_prompt: payload }
      : { test_prompt: 'Hello, this is a test.', ...payload }

    return apiClient.post(`/models/providers/${id}/test_connection/`, requestBody)
  },

  /**
   * 获取模型提供商的使用日志
   * @param {string} id - 提供商ID
   * @param {number} limit - 返回条数限制
   * @returns {Promise}
   */
  getProviderUsageLogs(id, limit = 100) {
    return apiClient.get(`/models/providers/${id}/usage_logs/`, {
      params: { limit }
    })
  },

  /**
   * 获取所有激活的模型提供商
   * @param {string} providerType - 提供商类型 (可选)
   * @returns {Promise}
   */
  getActiveProviders(providerType = null) {
    const params = providerType ? { provider_type: providerType } : {}
    return apiClient.get('/models/providers/active_providers/', { params })
  },

  /**
   * 按类型分组获取模型提供商
   * @returns {Promise} - 返回 {llm: [], text2image: [], image2video: [], image_edit: []}
   */
  getProvidersByType() {
    return apiClient.get('/models/providers/by_type/')
  },

  /**
   * 获取简化的模型提供商列表(仅id和name) - 用于下拉选择
   * @param {Object} params - 查询参数
   * @param {string} params.provider_type - 提供商类型 (llm/text2image/image2video/image_edit)
   * @returns {Promise} - 返回 {count, results: [{id, name}]}
   */
  getSimpleList(params = {}) {
    return apiClient.get('/models/providers/simple_list/', { params })
  },

  /**
   * 获取执行器选项列表
   * @param {string} providerType - 提供商类型 (可选，不传则返回所有类型)
   * @returns {Promise} - 返回执行器选项
   *
   * 返回格式:
   * - 指定类型: {provider_type: 'llm', executors: [{value, label}]}
   * - 所有类型: {llm: [{value, label}], text2image: [...], image2video: [...], image_edit: [...]}
   */
  getExecutorChoices(providerType = null) {
    const params = providerType ? { provider_type: providerType } : {}
    return apiClient.get('/models/providers/executor_choices/', { params })
  },

  getBuiltinVendors() {
    return apiClient.get('/models/providers/builtin_vendors/')
  },

  getVendorConnectionConfig(params) {
    return apiClient.get('/models/providers/vendor_connection_config/', { params })
  },

  updateVendorConnectionConfig(data) {
    return apiClient.put('/models/providers/vendor_connection_config/', data)
  },

  discoverVendorModels(data) {
    return apiClient.post('/models/providers/discover_vendor_models/', data)
  },

  batchCreateVendorModels(data) {
    return apiClient.post('/models/providers/batch_create_vendor_models/', data)
  }
}

/**
 * 模型使用日志相关 API
 */
export const modelUsageLogApi = {
  /**
   * 获取使用日志列表
   * @param {Object} params - 查询参数
   * @returns {Promise}
   */
  getUsageLogs(params = {}) {
    return apiClient.get('/models/usage-logs/', { params })
  },

  /**
   * 获取使用日志详情
   * @param {string} id - 日志ID
   * @returns {Promise}
   */
  getUsageLog(id) {
    return apiClient.get(`/models/usage-logs/${id}/`)
  },

  /**
   * 按项目获取使用日志
   * @param {string} projectId - 项目ID
   * @param {string} stageType - 阶段类型 (可选)
   * @returns {Promise}
   */
  getLogsByProject(projectId, stageType = null) {
    const params = { project_id: projectId }
    if (stageType) {
      params.stage_type = stageType
    }
    return apiClient.get('/models/usage-logs/by_project/', { params })
  },

  /**
   * 获取失败的使用日志
   * @param {number} limit - 返回条数限制
   * @returns {Promise}
   */
  getFailedLogs(limit = 100) {
    return apiClient.get('/models/usage-logs/failed_logs/', {
      params: { limit }
    })
  }
}

export default {
  modelProviderApi,
  modelUsageLogApi
}
