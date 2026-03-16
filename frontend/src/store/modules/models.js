/**
 * 模型管理 Vuex 模块
 * 职责: 管理模型提供商和使用日志的状态
 * 遵循单一职责原则(SRP)
 */

import { modelProviderApi, modelUsageLogApi } from '@/api/models'

const state = {
  // 模型提供商
  providers: [],
  currentProvider: null,
  activeProviders: [], // 激活的提供商
  providersByType: {
    llm: [],
    text2image: [],
    image2video: [],
    image_edit: []
  },

  // 使用日志
  usageLogs: [],
  currentUsageLog: null,

  // 统计信息
  providerStatistics: null,

  // 分页
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0
  },

  // 加载状态
  loading: {
    providers: false,
    currentProvider: false,
    usageLogs: false,
    testing: false
  }
}

const getters = {
  /**
   * 根据ID获取提供商
   */
  providerById: (state) => (id) => {
    return state.providers.find(p => p.id === id)
  },

  /**
   * 根据类型获取提供商
   */
  providersByType: (state) => (type) => {
    return state.providers.filter(p => p.provider_type === type)
  },

  /**
   * 获取激活的提供商
   */
  activeProviders: (state) => {
    return state.providers.filter(p => p.is_active)
  },

  /**
   * 获取激活的指定类型提供商
   */
  activeProvidersByType: (state) => (type) => {
    return state.providers.filter(p => p.provider_type === type && p.is_active)
  },

  /**
   * 获取LLM提供商
   */
  llmProviders: (state) => {
    return state.providersByType.llm
  },

  /**
   * 获取文生图提供商
   */
  text2imageProviders: (state) => {
    return state.providersByType.text2image
  },

  /**
   * 获取图生视频提供商
   */
  image2videoProviders: (state) => {
    return state.providersByType.image2video
  },

  /**
   * 获取图片编辑提供商
   */
  imageEditProviders: (state) => {
    return state.providersByType.image_edit
  }
}

const mutations = {
  SET_PROVIDERS(state, providers) {
    state.providers = providers
  },

  SET_CURRENT_PROVIDER(state, provider) {
    state.currentProvider = provider
  },

  SET_ACTIVE_PROVIDERS(state, providers) {
    state.activeProviders = providers
  },

  SET_PROVIDERS_BY_TYPE(state, data) {
    state.providersByType = data
  },

  SET_USAGE_LOGS(state, logs) {
    state.usageLogs = logs
  },

  SET_CURRENT_USAGE_LOG(state, log) {
    state.currentUsageLog = log
  },

  SET_PROVIDER_STATISTICS(state, statistics) {
    state.providerStatistics = statistics
  },

  SET_PAGINATION(state, pagination) {
    state.pagination = { ...state.pagination, ...pagination }
  },

  SET_LOADING(state, { key, value }) {
    state.loading[key] = value
  },

  ADD_PROVIDER(state, provider) {
    state.providers.unshift(provider)
  },

  UPDATE_PROVIDER(state, provider) {
    const index = state.providers.findIndex(p => p.id === provider.id)
    if (index !== -1) {
      state.providers.splice(index, 1, provider)
    }
    if (state.currentProvider && state.currentProvider.id === provider.id) {
      state.currentProvider = { ...state.currentProvider, ...provider }
    }
  },

  REMOVE_PROVIDER(state, id) {
    state.providers = state.providers.filter(p => p.id !== id)
    if (state.currentProvider && state.currentProvider.id === id) {
      state.currentProvider = null
    }
  }
}

const actions = {
  /**
   * 获取模型提供商列表
   */
  async fetchProviders({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'providers', value: true })
    try {
      const response = await modelProviderApi.getProviders(params)
      commit('SET_PROVIDERS', response.results || response)

      if (response.count !== undefined) {
        commit('SET_PAGINATION', {
          total: response.count
        })
      }

      return response
    } catch (error) {
      console.error('获取模型提供商列表失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'providers', value: false })
    }
  },

  /**
   * 获取模型提供商详情
   */
  async fetchProvider({ commit }, id) {
    commit('SET_LOADING', { key: 'currentProvider', value: true })
    try {
      const response = await modelProviderApi.getProvider(id)
      commit('SET_CURRENT_PROVIDER', response)
      return response
    } catch (error) {
      console.error('获取模型提供商详情失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'currentProvider', value: false })
    }
  },

  /**
   * 创建模型提供商
   */
  async createProvider({ commit }, data) {
    try {
      const response = await modelProviderApi.createProvider(data)
      commit('ADD_PROVIDER', response)
      return response
    } catch (error) {
      console.error('创建模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 更新模型提供商
   */
  async updateProvider({ commit }, { id, data }) {
    try {
      const response = await modelProviderApi.updateProvider(id, data)
      commit('UPDATE_PROVIDER', response)
      return response
    } catch (error) {
      console.error('更新模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 部分更新模型提供商
   */
  async patchProvider({ commit }, { id, data }) {
    try {
      const response = await modelProviderApi.patchProvider(id, data)
      commit('UPDATE_PROVIDER', response)
      return response
    } catch (error) {
      console.error('更新模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 删除模型提供商
   */
  async deleteProvider({ commit }, id) {
    try {
      await modelProviderApi.deleteProvider(id)
      commit('REMOVE_PROVIDER', id)
      return true
    } catch (error) {
      console.error('删除模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 切换模型提供商激活状态
   */
  async toggleProviderStatus({ commit }, id) {
    try {
      const response = await modelProviderApi.toggleProviderStatus(id)
      commit('UPDATE_PROVIDER', response.provider)
      return response
    } catch (error) {
      console.error('切换模型提供商状态失败:', error)
      throw error
    }
  },

  /**
   * 获取模型提供商统计信息
   */
  async fetchProviderStatistics({ commit }, id) {
    try {
      const response = await modelProviderApi.getProviderStatistics(id)
      commit('SET_PROVIDER_STATISTICS', response)
      return response
    } catch (error) {
      console.error('获取模型提供商统计信息失败:', error)
      throw error
    }
  },

  /**
   * 测试模型提供商连接
   */
  async testProviderConnection({ commit }, { id, testPrompt }) {
    commit('SET_LOADING', { key: 'testing', value: true })
    try {
      const response = await modelProviderApi.testProviderConnection(id, testPrompt)
      return response
    } catch (error) {
      console.error('测试模型提供商连接失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'testing', value: false })
    }
  },

  /**
   * 获取模型提供商的使用日志
   */
  async fetchProviderUsageLogs({ commit }, { id, limit = 100 }) {
    commit('SET_LOADING', { key: 'usageLogs', value: true })
    try {
      const response = await modelProviderApi.getProviderUsageLogs(id, limit)
      commit('SET_USAGE_LOGS', response.results || response)
      return response
    } catch (error) {
      console.error('获取使用日志失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'usageLogs', value: false })
    }
  },

  /**
   * 获取所有激活的模型提供商
   */
  async fetchActiveProviders({ commit }, providerType = null) {
    try {
      const response = await modelProviderApi.getActiveProviders(providerType)
      commit('SET_ACTIVE_PROVIDERS', response.results || response)
      return response
    } catch (error) {
      console.error('获取激活的模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 按类型分组获取模型提供商
   */
  async fetchProvidersByType({ commit }) {
    try {
      const response = await modelProviderApi.getProvidersByType()
      commit('SET_PROVIDERS_BY_TYPE', response)
      return response
    } catch (error) {
      console.error('按类型获取模型提供商失败:', error)
      throw error
    }
  },

  /**
   * 获取使用日志列表
   */
  async fetchUsageLogs({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'usageLogs', value: true })
    try {
      const response = await modelUsageLogApi.getUsageLogs(params)
      commit('SET_USAGE_LOGS', response.results || response)

      if (response.count !== undefined) {
        commit('SET_PAGINATION', {
          total: response.count
        })
      }

      return response
    } catch (error) {
      console.error('获取使用日志列表失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'usageLogs', value: false })
    }
  },

  /**
   * 获取使用日志详情
   */
  async fetchUsageLog({ commit }, id) {
    try {
      const response = await modelUsageLogApi.getUsageLog(id)
      commit('SET_CURRENT_USAGE_LOG', response)
      return response
    } catch (error) {
      console.error('获取使用日志详情失败:', error)
      throw error
    }
  },

  /**
   * 按项目获取使用日志
   */
  async fetchLogsByProject({ commit }, { projectId, stageType = null }) {
    commit('SET_LOADING', { key: 'usageLogs', value: true })
    try {
      const response = await modelUsageLogApi.getLogsByProject(projectId, stageType)
      commit('SET_USAGE_LOGS', response.results || response)
      return response
    } catch (error) {
      console.error('按项目获取使用日志失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'usageLogs', value: false })
    }
  },

  /**
   * 获取失败的使用日志
   */
  async fetchFailedLogs({ commit }, limit = 100) {
    commit('SET_LOADING', { key: 'usageLogs', value: true })
    try {
      const response = await modelUsageLogApi.getFailedLogs(limit)
      commit('SET_USAGE_LOGS', response.results || response)
      return response
    } catch (error) {
      console.error('获取失败日志失败:', error)
      throw error
    } finally {
      commit('SET_LOADING', { key: 'usageLogs', value: false })
    }
  }
}

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions
}
