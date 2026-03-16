import apiClient from '@/services/apiClient';

/**
 * 项目管理API服务
 */
export default {
  getSeries(params) {
    return apiClient.get('/projects/series/', { params });
  },

  getSeriesDetail(id) {
    return apiClient.get(`/projects/series/${id}/`);
  },

  createSeries(data) {
    return apiClient.post('/projects/series/', data);
  },

  updateSeries(id, data) {
    return apiClient.patch(`/projects/series/${id}/`, data);
  },

  deleteSeries(id) {
    return apiClient.delete(`/projects/series/${id}/`);
  },

  getProjects(params) {
    return apiClient.get('/projects/projects/', { params });
  },

  getProject(id) {
    return apiClient.get(`/projects/projects/${id}/`);
  },

  getAvailableAssets(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/available_assets/`);
  },

  getAssetBindings(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/asset_bindings/`);
  },

  updateAssetBindings(projectId, assetIds = []) {
    return apiClient.patch(`/projects/projects/${projectId}/asset_bindings/`, {
      asset_ids: assetIds,
    });
  },

  createProject(data) {
    return apiClient.post('/projects/projects/', data);
  },

  batchCreateProjects(data) {
    return apiClient.post('/projects/projects/batch_create/', data);
  },

  updateProject(id, data) {
    return apiClient.patch(`/projects/projects/${id}/`, data);
  },

  deleteProject(id) {
    return apiClient.delete(`/projects/projects/${id}/`);
  },

  getProjectStages(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/stages/`);
  },

  executeStage(projectId, stageName, inputData = {}, useStreaming = false) {
    return apiClient.post(`/projects/projects/${projectId}/execute_stage/`, {
      stage_name: stageName,
      input_data: inputData,
      use_streaming: useStreaming,
    });
  },

  retryStage(projectId, stageName) {
    return apiClient.post(`/projects/projects/${projectId}/retry_stage/`, {
      stage_name: stageName,
    });
  },

  pauseProject(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/pause/`);
  },

  resumeProject(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/resume/`);
  },

  rollbackStage(projectId, stageName) {
    return apiClient.post(`/projects/projects/${projectId}/rollback_stage/`, {
      stage_name: stageName,
    });
  },

  getModelConfig(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/model_config/`);
  },

  updateModelConfig(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_model_config/`, data);
  },

  saveAsTemplate(projectId, templateName, includeModelConfig = true) {
    return apiClient.post(`/projects/projects/${projectId}/save_as_template/`, {
      template_name: templateName,
      include_model_config: includeModelConfig,
    });
  },

  exportProject(projectId, options = {}) {
    return apiClient.post(`/projects/projects/${projectId}/export/`, {
      include_subtitles: options.includeSubtitles !== false,
      video_format: options.videoFormat || 'mp4',
    });
  },

  getStatistics() {
    return apiClient.get('/projects/projects/statistics/');
  },

  getAllStages(params) {
    return apiClient.get('/projects/stages/', { params });
  },

  getStage(stageId) {
    return apiClient.get(`/projects/stages/${stageId}/`);
  },

  updateStageData(projectId, stageName, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_stage_data/`, {
      stage_name: stageName,
      ...data,
    });
  },

  updateRewrite(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_rewrite/`, data);
  },

  updateStoryboard(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_storyboard/`, data);
  },

  updateCameraMovement(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_camera_movement/`, data);
  },

  initNodeChat(projectId, data) {
    return apiClient.post(`/projects/projects/${projectId}/node-chat-init/`, data);
  },

  getNodeChatStreamUrl(projectId, streamToken, accessToken) {
    const baseUrl = (process.env.VUE_APP_API_BASE_URL || '/api/v1').replace(/\/$/, '');
    const query = new URLSearchParams({ stream_token: streamToken });
    if (accessToken) {
      query.set('access_token', accessToken);
    }
    return `${baseUrl}/projects/projects/${projectId}/node-chat-stream/?${query.toString()}`;
  },

  runPipeline(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/run_pipeline/`);
  },

  retryPipeline(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/retry_pipeline/`);
  },

  forceReleaseQueue(projectId, reason = '') {
    return apiClient.post(`/projects/projects/${projectId}/force_release_queue/`, { reason });
  },

  generateJianyingDraft(projectId, options = {}) {
    return apiClient.post(`/projects/projects/${projectId}/generate_jianying_draft/`, options);
  },
};
