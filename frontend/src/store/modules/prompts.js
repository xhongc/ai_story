/**
 * 提示词管理Vuex模块
 * 职责: 管理提示词集和模板的状态
 * 遵循单一职责原则(SRP)
 */

import { promptSetAPI, promptTemplateAPI } from '@/api/prompts';

const state = {
  // 提示词集
  promptSets: [],
  currentPromptSet: null,
  promptSetsTotal: 0,
  promptSetsLoading: false,

  // 提示词模板
  promptTemplates: [],
  currentPromptTemplate: null,
  promptTemplatesTotal: 0,
  promptTemplatesLoading: false,

  // 版本历史
  templateVersions: [],
  versionsLoading: false,

  // 评估结果
  evaluationResult: null,
  evaluationLoading: false,

  // 预览结果
  previewResult: null,
  previewLoading: false,
};

const getters = {
  /**
   * 获取活跃的提示词集
   */
  activePromptSets: (state) => {
    return state.promptSets.filter((set) => set.is_active);
  },

  /**
   * 获取默认提示词集
   */
  defaultPromptSet: (state) => {
    return state.promptSets.find((set) => set.is_default);
  },

  /**
   * 根据阶段类型获取模板
   */
  getTemplateByStageType: (state) => (stageType) => {
    return state.promptTemplates.find(
      (template) => template.stage_type === stageType && template.is_active
    );
  },

  /**
   * 获取当前提示词集的模板列表
   */
  currentSetTemplates: (state) => {
    if (!state.currentPromptSet) return [];
    return state.promptTemplates.filter(
      (template) => template.template_set === state.currentPromptSet.id
    );
  },
};

const mutations = {
  // ===== 提示词集 =====
  SET_PROMPT_SETS(state, sets) {
    state.promptSets = sets;
  },

  SET_CURRENT_PROMPT_SET(state, set) {
    state.currentPromptSet = set;
  },

  SET_PROMPT_SETS_TOTAL(state, total) {
    state.promptSetsTotal = total;
  },

  SET_PROMPT_SETS_LOADING(state, loading) {
    state.promptSetsLoading = loading;
  },

  ADD_PROMPT_SET(state, set) {
    state.promptSets.unshift(set);
    state.promptSetsTotal += 1;
  },

  UPDATE_PROMPT_SET(state, updatedSet) {
    const index = state.promptSets.findIndex((set) => set.id === updatedSet.id);
    if (index !== -1) {
      state.promptSets.splice(index, 1, updatedSet);
    }
    if (state.currentPromptSet && state.currentPromptSet.id === updatedSet.id) {
      state.currentPromptSet = updatedSet;
    }
  },

  REMOVE_PROMPT_SET(state, id) {
    const index = state.promptSets.findIndex((set) => set.id === id);
    if (index !== -1) {
      state.promptSets.splice(index, 1);
      state.promptSetsTotal -= 1;
    }
    if (state.currentPromptSet && state.currentPromptSet.id === id) {
      state.currentPromptSet = null;
    }
  },

  // ===== 提示词模板 =====
  SET_PROMPT_TEMPLATES(state, templates) {
    state.promptTemplates = templates;
  },

  SET_CURRENT_PROMPT_TEMPLATE(state, template) {
    state.currentPromptTemplate = template;
  },

  SET_PROMPT_TEMPLATES_TOTAL(state, total) {
    state.promptTemplatesTotal = total;
  },

  SET_PROMPT_TEMPLATES_LOADING(state, loading) {
    state.promptTemplatesLoading = loading;
  },

  ADD_PROMPT_TEMPLATE(state, template) {
    state.promptTemplates.unshift(template);
    state.promptTemplatesTotal += 1;
  },

  UPDATE_PROMPT_TEMPLATE(state, updatedTemplate) {
    const index = state.promptTemplates.findIndex(
      (template) => template.id === updatedTemplate.id
    );
    if (index !== -1) {
      state.promptTemplates.splice(index, 1, updatedTemplate);
    }
    if (
      state.currentPromptTemplate &&
      state.currentPromptTemplate.id === updatedTemplate.id
    ) {
      state.currentPromptTemplate = updatedTemplate;
    }
    // 同时更新 currentPromptSet 中的 templates 数组
    if (state.currentPromptSet && state.currentPromptSet.templates) {
      const templateIndex = state.currentPromptSet.templates.findIndex(
        (template) => template.id === updatedTemplate.id
      );
      if (templateIndex !== -1) {
        state.currentPromptSet.templates.splice(templateIndex, 1, updatedTemplate);
      }
    }
  },

  REMOVE_PROMPT_TEMPLATE(state, id) {
    const index = state.promptTemplates.findIndex((template) => template.id === id);
    if (index !== -1) {
      state.promptTemplates.splice(index, 1);
      state.promptTemplatesTotal -= 1;
    }
    if (state.currentPromptTemplate && state.currentPromptTemplate.id === id) {
      state.currentPromptTemplate = null;
    }
    // 同时从 currentPromptSet 中移除
    if (state.currentPromptSet && state.currentPromptSet.templates) {
      const templateIndex = state.currentPromptSet.templates.findIndex(
        (template) => template.id === id
      );
      if (templateIndex !== -1) {
        state.currentPromptSet.templates.splice(templateIndex, 1);
        // 更新模板计数
        if (state.currentPromptSet.templates_count) {
          state.currentPromptSet.templates_count -= 1;
        }
      }
    }
  },

  // ===== 版本历史 =====
  SET_TEMPLATE_VERSIONS(state, versions) {
    state.templateVersions = versions;
  },

  SET_VERSIONS_LOADING(state, loading) {
    state.versionsLoading = loading;
  },

  // ===== 评估结果 =====
  SET_EVALUATION_RESULT(state, result) {
    state.evaluationResult = result;
  },

  SET_EVALUATION_LOADING(state, loading) {
    state.evaluationLoading = loading;
  },

  // ===== 预览结果 =====
  SET_PREVIEW_RESULT(state, result) {
    state.previewResult = result;
  },

  SET_PREVIEW_LOADING(state, loading) {
    state.previewLoading = loading;
  },

  // ===== 重置 =====
  RESET_STATE(state) {
    state.currentPromptSet = null;
    state.currentPromptTemplate = null;
    state.templateVersions = [];
    state.evaluationResult = null;
    state.previewResult = null;
  },
};

const actions = {
  // ===== 提示词集操作 =====

  /**
   * 获取提示词集列表
   */
  async fetchPromptSets({ commit }, params = {}) {
    commit('SET_PROMPT_SETS_LOADING', true);
    try {
      const response = await promptSetAPI.getList(params);
      commit('SET_PROMPT_SETS', response.results || response);
      commit('SET_PROMPT_SETS_TOTAL', response.count || response.length);
      return response;
    } catch (error) {
      console.error('获取提示词集列表失败:', error);
      throw error;
    } finally {
      commit('SET_PROMPT_SETS_LOADING', false);
    }
  },

  /**
   * 获取提示词集详情
   */
  async fetchPromptSetDetail({ commit }, id) {
    commit('SET_PROMPT_SETS_LOADING', true);
    try {
      const response = await promptSetAPI.getDetail(id);
      commit('SET_CURRENT_PROMPT_SET', response);
      return response;
    } catch (error) {
      console.error('获取提示词集详情失败:', error);
      throw error;
    } finally {
      commit('SET_PROMPT_SETS_LOADING', false);
    }
  },

  /**
   * 创建提示词集
   */
  async createPromptSet({ commit }, data) {
    try {
      const response = await promptSetAPI.create(data);
      commit('ADD_PROMPT_SET', response);
      return response;
    } catch (error) {
      console.error('创建提示词集失败:', error);
      throw error;
    }
  },

  /**
   * 更新提示词集
   */
  async updatePromptSet({ commit }, { id, data }) {
    try {
      const response = await promptSetAPI.update(id, data);
      commit('UPDATE_PROMPT_SET', response);
      return response;
    } catch (error) {
      console.error('更新提示词集失败:', error);
      throw error;
    }
  },

  /**
   * 删除提示词集
   */
  async deletePromptSet({ commit }, id) {
    try {
      await promptSetAPI.delete(id);
      commit('REMOVE_PROMPT_SET', id);
    } catch (error) {
      console.error('删除提示词集失败:', error);
      throw error;
    }
  },

  /**
   * 克隆提示词集
   */
  async clonePromptSet({ commit }, { id, name }) {
    try {
      const response = await promptSetAPI.clone(id, name);
      commit('ADD_PROMPT_SET', response);
      return response;
    } catch (error) {
      console.error('克隆提示词集失败:', error);
      throw error;
    }
  },

  /**
   * 设置为默认提示词集
   */
  async setDefaultPromptSet({ commit, state }, id) {
    try {
      const response = await promptSetAPI.setDefault(id);
      // 更新所有提示词集的is_default状态
      state.promptSets.forEach((set) => {
        commit('UPDATE_PROMPT_SET', {
          ...set,
          is_default: set.id === id,
        });
      });
      return response;
    } catch (error) {
      console.error('设置默认提示词集失败:', error);
      throw error;
    }
  },

  /**
   * 获取默认提示词集
   */
  async fetchDefaultPromptSet({ commit }) {
    try {
      const response = await promptSetAPI.getDefault();
      commit('SET_CURRENT_PROMPT_SET', response);
      return response;
    } catch (error) {
      console.error('获取默认提示词集失败:', error);
      throw error;
    }
  },

  // ===== 提示词模板操作 =====

  /**
   * 获取提示词模板列表
   */
  async fetchPromptTemplates({ commit }, params = {}) {
    commit('SET_PROMPT_TEMPLATES_LOADING', true);
    try {
      const response = await promptTemplateAPI.getList(params);
      commit('SET_PROMPT_TEMPLATES', response.results || response);
      commit('SET_PROMPT_TEMPLATES_TOTAL', response.count || response.length);
      return response;
    } catch (error) {
      console.error('获取提示词模板列表失败:', error);
      throw error;
    } finally {
      commit('SET_PROMPT_TEMPLATES_LOADING', false);
    }
  },

  /**
   * 获取提示词模板详情
   */
  async fetchPromptTemplateDetail({ commit }, id) {
    commit('SET_PROMPT_TEMPLATES_LOADING', true);
    try {
      const response = await promptTemplateAPI.getDetail(id);
      commit('SET_CURRENT_PROMPT_TEMPLATE', response);
      return response;
    } catch (error) {
      console.error('获取提示词模板详情失败:', error);
      throw error;
    } finally {
      commit('SET_PROMPT_TEMPLATES_LOADING', false);
    }
  },

  /**
   * 创建提示词模板
   */
  async createPromptTemplate({ commit }, data) {
    try {
      const response = await promptTemplateAPI.create(data);
      commit('ADD_PROMPT_TEMPLATE', response);
      return response;
    } catch (error) {
      console.error('创建提示词模板失败:', error);
      throw error;
    }
  },

  /**
   * 更新提示词模板
   */
  async updatePromptTemplate({ commit }, { id, data }) {
    try {
      const response = await promptTemplateAPI.update(id, data);
      commit('UPDATE_PROMPT_TEMPLATE', response);
      return response;
    } catch (error) {
      console.error('更新提示词模板失败:', error);
      throw error;
    }
  },

  /**
   * 部分更新提示词模板（用于快捷更新激活状态等）
   */
  async partialUpdatePromptTemplate({ commit }, { id, data }) {
    try {
      const response = await promptTemplateAPI.partialUpdate(id, data);
      commit('UPDATE_PROMPT_TEMPLATE', response);
      return response;
    } catch (error) {
      console.error('部分更新提示词模板失败:', error);
      throw error;
    }
  },

  /**
   * 删除提示词模板
   */
  async deletePromptTemplate({ commit }, id) {
    try {
      await promptTemplateAPI.delete(id);
      commit('REMOVE_PROMPT_TEMPLATE', id);
    } catch (error) {
      console.error('删除提示词模板失败:', error);
      throw error;
    }
  },

  /**
   * 创建新版本
   */
  async createTemplateVersion({ commit }, { id, data }) {
    try {
      const response = await promptTemplateAPI.createVersion(id, data);
      commit('ADD_PROMPT_TEMPLATE', response);
      return response;
    } catch (error) {
      console.error('创建新版本失败:', error);
      throw error;
    }
  },

  /**
   * 获取版本历史
   */
  async fetchTemplateVersions({ commit }, id) {
    commit('SET_VERSIONS_LOADING', true);
    try {
      const response = await promptTemplateAPI.getVersions(id);
      commit('SET_TEMPLATE_VERSIONS', response);
      return response;
    } catch (error) {
      console.error('获取版本历史失败:', error);
      throw error;
    } finally {
      commit('SET_VERSIONS_LOADING', false);
    }
  },

  /**
   * 验证模板语法
   */
  async validateTemplate(_, { id, templateContent }) {
    try {
      const response = await promptTemplateAPI.validate(id, templateContent);
      return response;
    } catch (error) {
      console.error('验证模板语法失败:', error);
      throw error;
    }
  },

  /**
   * 预览模板渲染结果
   */
  async previewTemplate({ commit }, { id, variables }) {
    commit('SET_PREVIEW_LOADING', true);
    try {
      const response = await promptTemplateAPI.preview(id, variables);
      commit('SET_PREVIEW_RESULT', response);
      return response;
    } catch (error) {
      console.error('预览模板失败:', error);
      throw error;
    } finally {
      commit('SET_PREVIEW_LOADING', false);
    }
  },

  /**
   * AI评估提示词效果
   */
  async evaluateTemplate({ commit }, id) {
    commit('SET_EVALUATION_LOADING', true);
    try {
      const response = await promptTemplateAPI.evaluate(id);
      commit('SET_EVALUATION_RESULT', response);
      return response;
    } catch (error) {
      console.error('评估提示词失败:', error);
      throw error;
    } finally {
      commit('SET_EVALUATION_LOADING', false);
    }
  },

  /**
   * 重置状态
   */
  resetState({ commit }) {
    commit('RESET_STATE');
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
