import projectApi from '@/api/projects';

const state = {
  projects: [],
  currentProject: null,
  stages: [],
  modelConfig: null,
  statistics: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
  loading: {
    projects: false,
    currentProject: false,
    stages: false,
  },
};

const getters = {
  projectById: (state) => (id) => {
    return state.projects.find((p) => p.id === id);
  },
  projectsByStatus: (state) => (status) => {
    return state.projects.filter((p) => p.status === status);
  },
  stageByType: (state) => (stageType) => {
    return state.stages.find((s) => s.stage_type === stageType);
  },
  completedStagesCount: (state) => {
    return state.stages.filter((s) => s.status === 'completed').length;
  },
  progressPercentage: (state, getters) => {
    const total = state.stages.length;
    if (total === 0) return 0;
    return Math.round((getters.completedStagesCount / total) * 100);
  },
};

const mutations = {
  SET_PROJECTS(state, projects) {
    state.projects = projects;
  },
  SET_CURRENT_PROJECT(state, project) {
    state.currentProject = project;
  },
  SET_STAGES(state, stages) {
    state.stages = stages;
  },
  SET_MODEL_CONFIG(state, config) {
    state.modelConfig = config;
  },
  SET_STATISTICS(state, statistics) {
    state.statistics = statistics;
  },
  SET_PAGINATION(state, pagination) {
    state.pagination = { ...state.pagination, ...pagination };
  },
  SET_LOADING(state, { key, value }) {
    state.loading[key] = value;
  },
  ADD_PROJECT(state, project) {
    state.projects.unshift(project);
    if (state.statistics) {
      state.statistics.total_projects += 1;
      state.statistics[`${project.status}_projects`] =
        (state.statistics[`${project.status}_projects`] || 0) + 1;
    }
  },
  UPDATE_PROJECT(state, project) {
    const index = state.projects.findIndex((p) => p.id === project.id);
    if (index !== -1) {
      state.projects.splice(index, 1, project);
    }
    if (state.currentProject && state.currentProject.id === project.id) {
      state.currentProject = { ...state.currentProject, ...project };
    }
  },
  REMOVE_PROJECT(state, id) {
    const project = state.projects.find((p) => p.id === id);
    state.projects = state.projects.filter((p) => p.id !== id);
    if (state.statistics && project) {
      state.statistics.total_projects -= 1;
      state.statistics[`${project.status}_projects`] -= 1;
    }
  },
  UPDATE_STAGE(state, stage) {
    const index = state.stages.findIndex((s) => s.id === stage.id);
    if (index !== -1) {
      state.stages.splice(index, 1, stage);
    }
  },
};

const actions = {
  // 获取项目列表
  async fetchProjects({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'projects', value: true });
    try {
      const response = await projectApi.getProjects(params);
      commit('SET_PROJECTS', response.results);
      commit('SET_PAGINATION', {
        total: response.count,
        page: params.page || 1,
      });
      return response;
    } catch (error) {
      console.error('获取项目列表失败:', error);
      throw error;
    } finally {
      commit('SET_LOADING', { key: 'projects', value: false });
    }
  },

  // 获取项目详情
  async fetchProject({ commit }, id) {
    commit('SET_LOADING', { key: 'currentProject', value: true });
    try {
      const project = await projectApi.getProject(id);
      commit('SET_CURRENT_PROJECT', project);
      // 如果响应包含stages,也更新stages
      if (project.stages) {
        commit('SET_STAGES', project.stages);
      }
      return project;
    } catch (error) {
      console.error('获取项目详情失败:', error);
      throw error;
    } finally {
      commit('SET_LOADING', { key: 'currentProject', value: false });
    }
  },

  // 创建项目
  async createProject({ commit }, data) {
    try {
      const project = await projectApi.createProject(data);
      commit('ADD_PROJECT', project);
      return project;
    } catch (error) {
      console.error('创建项目失败:', error);
      throw error;
    }
  },

  // 更新项目
  async updateProject({ commit }, { id, data }) {
    try {
      const project = await projectApi.updateProject(id, data);
      commit('UPDATE_PROJECT', project);
      return project;
    } catch (error) {
      console.error('更新项目失败:', error);
      throw error;
    }
  },

  // 删除项目
  async deleteProject({ commit }, id) {
    try {
      await projectApi.deleteProject(id);
      commit('REMOVE_PROJECT', id);
    } catch (error) {
      console.error('删除项目失败:', error);
      throw error;
    }
  },

  // 获取项目阶段
  async fetchProjectStages({ commit }, projectId) {
    commit('SET_LOADING', { key: 'stages', value: true });
    try {
      const stages = await projectApi.getProjectStages(projectId);
      commit('SET_STAGES', stages);
      return stages;
    } catch (error) {
      console.error('获取项目阶段失败:', error);
      throw error;
    } finally {
      commit('SET_LOADING', { key: 'stages', value: false });
    }
  },

  // 执行阶段
  async executeStage({ commit }, { projectId, stageName, inputData }) {
    try {
      console.log(333, projectId, stageName, inputData)
      const result = await projectApi.executeStage(projectId, stageName, inputData);
      if (result.project) {
        commit('UPDATE_PROJECT', result.project);
      }
      if (result.stage) {
        commit('UPDATE_STAGE', result.stage);
      }
      return result;
    } catch (error) {
      console.error('执行阶段失败:', error);
      throw error;
    }
  },

  // 重试阶段
  async retryStage({ commit }, { projectId, stageName }) {
    try {
      const result = await projectApi.retryStage(projectId, stageName);
      if (result.stage) {
        commit('UPDATE_STAGE', result.stage);
      }
      return result;
    } catch (error) {
      console.error('重试阶段失败:', error);
      throw error;
    }
  },

  // 暂停项目
  async pauseProject({ commit }, projectId) {
    try {
      const result = await projectApi.pauseProject(projectId);
      if (result.project) {
        commit('UPDATE_PROJECT', result.project);
      }
      return result;
    } catch (error) {
      console.error('暂停项目失败:', error);
      throw error;
    }
  },

  // 恢复项目
  async resumeProject({ commit }, projectId) {
    try {
      const result = await projectApi.resumeProject(projectId);
      if (result.project) {
        commit('UPDATE_PROJECT', result.project);
      }
      return result;
    } catch (error) {
      console.error('恢复项目失败:', error);
      throw error;
    }
  },

  // 回滚阶段
  async rollbackStage({ commit }, { projectId, stageName }) {
    try {
      const result = await projectApi.rollbackStage(projectId, stageName);
      if (result.project) {
        commit('UPDATE_PROJECT', result.project);
      }
      // 重新获取阶段信息
      const stages = await projectApi.getProjectStages(projectId);
      commit('SET_STAGES', stages);
      return result;
    } catch (error) {
      console.error('回滚阶段失败:', error);
      throw error;
    }
  },

  // 获取模型配置
  async fetchModelConfig({ commit }, projectId) {
    try {
      const config = await projectApi.getModelConfig(projectId);
      commit('SET_MODEL_CONFIG', config);
      return config;
    } catch (error) {
      console.error('获取模型配置失败:', error);
      throw error;
    }
  },

  // 更新模型配置
  async updateModelConfig({ commit }, { projectId, data }) {
    try {
      const config = await projectApi.updateModelConfig(projectId, data);
      commit('SET_MODEL_CONFIG', config);
      return config;
    } catch (error) {
      console.error('更新模型配置失败:', error);
      throw error;
    }
  },

  // 保存为模板
  async saveAsTemplate({ commit }, { projectId, templateName, includeModelConfig }) {
    try {
      const result = await projectApi.saveAsTemplate(projectId, templateName, includeModelConfig);
      return result;
    } catch (error) {
      console.error('保存模板失败:', error);
      throw error;
    }
  },

  // 导出项目
  async exportProject({ commit }, { projectId, options }) {
    try {
      const result = await projectApi.exportProject(projectId, options);
      return result;
    } catch (error) {
      console.error('导出项目失败:', error);
      throw error;
    }
  },

  // 获取统计信息
  async fetchStatistics({ commit }) {
    try {
      const statistics = await projectApi.getStatistics();
      commit('SET_STATISTICS', statistics);
      return statistics;
    } catch (error) {
      console.error('获取统计信息失败:', error);
      throw error;
    }
  },

  // 清空当前项目
  clearCurrentProject({ commit }) {
    commit('SET_CURRENT_PROJECT', null);
    commit('SET_STAGES', []);
    commit('SET_MODEL_CONFIG', null);
  },

  // 更新阶段数据
  async updateStageData({ commit }, { projectId, stageName, data }) {
    try {
      const result = await projectApi.updateStageData(projectId, stageName, data);
      // 后端返回 { message, stage }
      if (result.stage) {
        commit('UPDATE_STAGE', result.stage);
        return result.stage;
      }
      return result;
    } catch (error) {
      console.error('更新阶段数据失败:', error);
      throw error;
    }
  },

  // 生成剪映草稿
  async generateJianyingDraft({ commit }, { projectId, options }) {
    try {
      const result = await projectApi.generateJianyingDraft(projectId, options);
      // 返回 { task_id, channel, message, websocket_url }
      return result;
    } catch (error) {
      console.error('生成剪映草稿失败:', error);
      throw error;
    }
  },

  // 运行完整工作流
  async runPipeline({ commit }, { projectId }) {
    try {
      const result = await projectApi.runPipeline(projectId);
      // 返回 { task_id, channel, message, project_id }
      return result;
    } catch (error) {
      console.error('运行工作流失败:', error);
      throw error;
    }
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
