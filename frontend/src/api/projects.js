import apiClient from '@/services/apiClient';

/**
 * 项目管理API服务
 */
export default {
  /**
   * 获取项目列表
   * @param {Object} params - 查询参数 {page, pageSize, status, search, ordering}
   */
  getProjects(params) {
    return apiClient.get('/projects/projects/', { params });
  },

  /**
   * 获取单个项目详情
   * @param {String} id - 项目ID
   */
  getProject(id) {
    return apiClient.get(`/projects/projects/${id}/`);
  },

  /**
   * 创建项目
   * @param {Object} data - 项目数据 {name, description, original_topic, prompt_template_set}
   */
  createProject(data) {
    return apiClient.post('/projects/projects/', data);
  },

  /**
   * 更新项目
   * @param {String} id - 项目ID
   * @param {Object} data - 更新数据
   */
  updateProject(id, data) {
    return apiClient.patch(`/projects/projects/${id}/`, data);
  },

  /**
   * 删除项目
   * @param {String} id - 项目ID
   */
  deleteProject(id) {
    return apiClient.delete(`/projects/projects/${id}/`);
  },

  /**
   * 获取项目所有阶段
   * @param {String} projectId - 项目ID
   */
  getProjectStages(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/stages/`);
  },

  /**
   * 执行项目阶段
   * @param {String} projectId - 项目ID
   * @param {String} stageName - 阶段名称
   * @param {Object} inputData - 输入数据(可选)
   * @param {Boolean} useStreaming - 是否启用SSE流式输出(可选)
   */
  executeStage(projectId, stageName, inputData = {}, useStreaming = false) {
    console.log(444, projectId, stageName, inputData, useStreaming);

    return apiClient.post(`/projects/projects/${projectId}/execute_stage/`, {
      stage_name: stageName,
      input_data: inputData,
      use_streaming: useStreaming,
    });
  },

  /**
   * 重试失败的阶段
   * @param {String} projectId - 项目ID
   * @param {String} stageName - 阶段名称
   */
  retryStage(projectId, stageName) {
    return apiClient.post(`/projects/projects/${projectId}/retry_stage/`, {
      stage_name: stageName,
    });
  },

  /**
   * 暂停项目
   * @param {String} projectId - 项目ID
   */
  pauseProject(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/pause/`);
  },

  /**
   * 恢复项目
   * @param {String} projectId - 项目ID
   */
  resumeProject(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/resume/`);
  },

  /**
   * 回滚到指定阶段
   * @param {String} projectId - 项目ID
   * @param {String} stageName - 阶段名称
   */
  rollbackStage(projectId, stageName) {
    return apiClient.post(`/projects/projects/${projectId}/rollback_stage/`, {
      stage_name: stageName,
    });
  },

  /**
   * 获取项目模型配置
   * @param {String} projectId - 项目ID
   */
  getModelConfig(projectId) {
    return apiClient.get(`/projects/projects/${projectId}/model_config/`);
  },

  /**
   * 更新项目模型配置
   * @param {String} projectId - 项目ID
   * @param {Object} data - 配置数据
   */
  updateModelConfig(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_model_config/`, data);
  },

  /**
   * 将项目保存为模板
   * @param {String} projectId - 项目ID
   * @param {String} templateName - 模板名称
   * @param {Boolean} includeModelConfig - 是否包含模型配置
   */
  saveAsTemplate(projectId, templateName, includeModelConfig = true) {
    return apiClient.post(`/projects/projects/${projectId}/save_as_template/`, {
      template_name: templateName,
      include_model_config: includeModelConfig,
    });
  },

  /**
   * 导出项目
   * @param {String} projectId - 项目ID
   * @param {Object} options - 导出选项 {include_subtitles, video_format}
   */
  exportProject(projectId, options = {}) {
    return apiClient.post(`/projects/projects/${projectId}/export/`, {
      include_subtitles: options.includeSubtitles !== false,
      video_format: options.videoFormat || 'mp4',
    });
  },

  /**
   * 获取项目统计信息
   */
  getStatistics() {
    return apiClient.get('/projects/projects/statistics/');
  },

  /**
   * 获取所有项目阶段(全局)
   * @param {Object} params - 查询参数
   */
  getAllStages(params) {
    return apiClient.get('/projects/stages/', { params });
  },

  /**
   * 获取单个阶段详情
   * @param {String} stageId - 阶段ID
   */
  getStage(stageId) {
    return apiClient.get(`/projects/stages/${stageId}/`);
  },

  /**
   * 更新阶段数据
   * @param {String} projectId - 项目ID
   * @param {String} stageName - 阶段名称
   * @param {Object} data - 更新数据 {input_data, output_data}
   */
  updateStageData(projectId, stageName, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_stage_data/`, {
      stage_name: stageName,
      ...data,
    });
  },

  /**
   * 更新文案改写
   * @param {String} projectId - 项目ID
   * @param {Object} data - 更新数据 {rewritten_text, original_text?}
   */
  updateRewrite(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_rewrite/`, data);
  },

  /**
   * 更新分镜内容
   * @param {String} projectId - 项目ID
   * @param {Object} data - 更新数据 {storyboard_id, scene_description?, narration_text?, image_prompt?, duration_seconds?}
   */
  updateStoryboard(projectId, data) {
    return apiClient.patch(`/projects/projects/${projectId}/update_storyboard/`, data);
  },

  /**
   * 运行完整工作流（智能跳过已完成阶段）
   * @param {String} projectId - 项目ID
   */
  runPipeline(projectId) {
    return apiClient.post(`/projects/projects/${projectId}/run_pipeline/`);
  },

  /**
   * 生成剪映草稿
   * @param {String} projectId - 项目ID
   * @param {Object} options - 可选参数
   *   {
   *     background_music: String,      // 背景音乐路径
   *     draft_folder_path: String,     // 草稿保存路径
   *     music_volume: Number,          // 音乐音量 (0-1)
   *     add_intro_animation: Boolean,  // 是否添加入场动画
   *     subtitle_size: Number,         // 字幕大小
   *     width: Number,                 // 视频宽度
   *     height: Number                 // 视频高度
   *   }
   */
  generateJianyingDraft(projectId, options = {}) {
    return apiClient.post(`/projects/projects/${projectId}/generate_jianying_draft/`, options);
  },
};
