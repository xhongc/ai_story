import projectApi from '@/api/projects';

const state = {
  seriesList: [],
  currentSeries: null,
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
    series: false,
    currentSeries: false,
    projects: false,
    currentProject: false,
    stages: false,
  },
};

const getters = {
  projectById: (state) => (id) => state.projects.find((p) => p.id === id),
  stageByType: (state) => (stageType) => state.stages.find((s) => s.stage_type === stageType),
  completedStagesCount: (state) => state.stages.filter((s) => s.status === 'completed').length,
  progressPercentage: (state, getters) => {
    const total = state.stages.length;
    if (total === 0) return 0;
    return Math.round((getters.completedStagesCount / total) * 100);
  },
};

const mutations = {
  SET_SERIES(state, seriesList) {
    state.seriesList = seriesList;
  },
  SET_CURRENT_SERIES(state, series) {
    state.currentSeries = series;
  },
  ADD_SERIES(state, series) {
    state.seriesList.unshift(series);
  },
  UPDATE_SERIES(state, series) {
    const index = state.seriesList.findIndex((item) => item.id === series.id);
    if (index !== -1) {
      state.seriesList.splice(index, 1, series);
    }
    if (state.currentSeries && state.currentSeries.id === series.id) {
      state.currentSeries = { ...state.currentSeries, ...series };
    }
  },
  REMOVE_SERIES(state, id) {
    state.seriesList = state.seriesList.filter((item) => item.id !== id);
  },
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
  },
  UPDATE_PROJECT(state, project) {
    const index = state.projects.findIndex((p) => p.id === project.id);
    if (index !== -1) {
      state.projects.splice(index, 1, project);
    }
    if (state.currentProject && state.currentProject.id === project.id) {
      state.currentProject = { ...state.currentProject, ...project };
    }
    if (state.currentSeries && Array.isArray(state.currentSeries.episodes)) {
      const episodeIndex = state.currentSeries.episodes.findIndex((item) => item.id === project.id);
      if (episodeIndex !== -1) {
        state.currentSeries.episodes.splice(episodeIndex, 1, {
          ...state.currentSeries.episodes[episodeIndex],
          ...project,
        });
      }
    }
  },
  REMOVE_PROJECT(state, id) {
    state.projects = state.projects.filter((p) => p.id !== id);
    if (state.currentSeries && Array.isArray(state.currentSeries.episodes)) {
      state.currentSeries.episodes = state.currentSeries.episodes.filter((item) => item.id !== id);
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
  async fetchSeries({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'series', value: true });
    try {
      const response = await projectApi.getSeries(params);
      commit('SET_SERIES', response.results || response);
      return response;
    } finally {
      commit('SET_LOADING', { key: 'series', value: false });
    }
  },

  async fetchSeriesDetail({ commit }, id) {
    commit('SET_LOADING', { key: 'currentSeries', value: true });
    try {
      const series = await projectApi.getSeriesDetail(id);
      commit('SET_CURRENT_SERIES', series);
      return series;
    } finally {
      commit('SET_LOADING', { key: 'currentSeries', value: false });
    }
  },

  async createSeries({ commit }, data) {
    const series = await projectApi.createSeries(data);
    commit('ADD_SERIES', series);
    return series;
  },

  async updateSeries({ commit }, { id, data }) {
    const series = await projectApi.updateSeries(id, data);
    commit('UPDATE_SERIES', series);
    return series;
  },

  async deleteSeries({ commit }, id) {
    await projectApi.deleteSeries(id);
    commit('REMOVE_SERIES', id);
  },

  async fetchProjects({ commit }, params = {}) {
    commit('SET_LOADING', { key: 'projects', value: true });
    try {
      const response = await projectApi.getProjects(params);
      commit('SET_PROJECTS', response.results || []);
      commit('SET_PAGINATION', {
        total: response.count || 0,
        page: params.page || 1,
      });
      return response;
    } finally {
      commit('SET_LOADING', { key: 'projects', value: false });
    }
  },

  async fetchProject({ commit }, id) {
    commit('SET_LOADING', { key: 'currentProject', value: true });
    try {
      const project = await projectApi.getProject(id);
      commit('SET_CURRENT_PROJECT', project);
      if (project.stages) {
        commit('SET_STAGES', project.stages);
      }
      return project;
    } finally {
      commit('SET_LOADING', { key: 'currentProject', value: false });
    }
  },

  async createProject({ commit }, data) {
    const project = await projectApi.createProject(data);
    commit('ADD_PROJECT', project);
    return project;
  },

  async updateProject({ commit }, { id, data }) {
    const project = await projectApi.updateProject(id, data);
    commit('UPDATE_PROJECT', project);
    return project;
  },

  async deleteProject({ commit }, id) {
    await projectApi.deleteProject(id);
    commit('REMOVE_PROJECT', id);
  },

  async fetchProjectStages({ commit }, projectId) {
    commit('SET_LOADING', { key: 'stages', value: true });
    try {
      const stages = await projectApi.getProjectStages(projectId);
      commit('SET_STAGES', stages);
      return stages;
    } finally {
      commit('SET_LOADING', { key: 'stages', value: false });
    }
  },

  async executeStage({ commit }, { projectId, stageName, inputData }) {
    const result = await projectApi.executeStage(projectId, stageName, inputData);
    if (result.project) {
      commit('UPDATE_PROJECT', result.project);
    }
    if (result.stage) {
      commit('UPDATE_STAGE', result.stage);
    }
    return result;
  },

  async retryStage({ commit }, { projectId, stageName }) {
    const result = await projectApi.retryStage(projectId, stageName);
    if (result.stage) {
      commit('UPDATE_STAGE', result.stage);
    }
    return result;
  },

  async pauseProject({ commit }, projectId) {
    const result = await projectApi.pauseProject(projectId);
    if (result.project) {
      commit('UPDATE_PROJECT', result.project);
    }
    return result;
  },

  async resumeProject({ commit }, projectId) {
    const result = await projectApi.resumeProject(projectId);
    if (result.project) {
      commit('UPDATE_PROJECT', result.project);
    }
    return result;
  },

  async rollbackStage({ commit }, { projectId, stageName }) {
    const result = await projectApi.rollbackStage(projectId, stageName);
    if (result.project) {
      commit('UPDATE_PROJECT', result.project);
    }
    return result;
  },

  async fetchModelConfig({ commit }, projectId) {
    const config = await projectApi.getModelConfig(projectId);
    commit('SET_MODEL_CONFIG', config);
    return config;
  },

  async updateModelConfig({ commit }, { projectId, data }) {
    const config = await projectApi.updateModelConfig(projectId, data);
    commit('SET_MODEL_CONFIG', config);
    return config;
  },

  async saveAsTemplate(context, { projectId, templateName, includeModelConfig }) {
    return projectApi.saveAsTemplate(projectId, templateName, includeModelConfig);
  },

  async exportProject(context, { projectId, options }) {
    return projectApi.exportProject(projectId, options);
  },

  async fetchStatistics({ commit }) {
    const statistics = await projectApi.getStatistics();
    commit('SET_STATISTICS', statistics);
    return statistics;
  },

  clearCurrentProject({ commit }) {
    commit('SET_CURRENT_PROJECT', null);
    commit('SET_STAGES', []);
    commit('SET_MODEL_CONFIG', null);
  },

  clearCurrentSeries({ commit }) {
    commit('SET_CURRENT_SERIES', null);
  },

  async updateStageData({ commit }, { projectId, stageName, data }) {
    const result = await projectApi.updateStageData(projectId, stageName, data);
    if (result.stage) {
      commit('UPDATE_STAGE', result.stage);
      return result.stage;
    }
    return result;
  },

  async updateRewrite(context, { projectId, data }) {
    return projectApi.updateRewrite(projectId, data);
  },

  async updateStoryboard(context, { projectId, storyboardId, data }) {
    const payload = { storyboard_id: storyboardId, ...data };
    return projectApi.updateStoryboard(projectId, payload);
  },

  async updateCameraMovement(context, { projectId, cameraId, data }) {
    const payload = { camera_id: cameraId, ...data };
    return projectApi.updateCameraMovement(projectId, payload);
  },

  async generateJianyingDraft(context, { projectId, options }) {
    return projectApi.generateJianyingDraft(projectId, options);
  },

  async runPipeline(context, { projectId }) {
    return projectApi.runPipeline(projectId);
  },
};

export default {
  namespaced: true,
  state,
  getters,
  mutations,
  actions,
};
