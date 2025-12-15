/**
 * 提示词管理API服务
 * 职责: 封装所有提示词相关的API调用
 * 遵循单一职责原则(SRP)
 */

import apiClient from '@/services/apiClient';

/**
 * 提示词集API
 */
export const promptSetAPI = {
  /**
   * 获取提示词集列表
   * @param {Object} params - 查询参数 {is_active, is_default, created_by, search, page, page_size}
   * @returns {Promise}
   */
  getList(params = {}) {
    return apiClient({
      url: '/prompts/sets/',
      method: 'get',
      params,
    });
  },

  /**
   * 获取提示词集详情
   * @param {String} id - 提示词集ID
   * @returns {Promise}
   */
  getDetail(id) {
    return apiClient({
      url: `/prompts/sets/${id}/`,
      method: 'get',
    });
  },

  /**
   * 创建提示词集
   * @param {Object} data - {name, description, is_active, is_default}
   * @returns {Promise}
   */
  create(data) {
    return apiClient({
      url: '/prompts/sets/',
      method: 'post',
      data,
    });
  },

  /**
   * 更新提示词集
   * @param {String} id - 提示词集ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  update(id, data) {
    return apiClient({
      url: `/prompts/sets/${id}/`,
      method: 'put',
      data,
    });
  },

  /**
   * 部分更新提示词集
   * @param {String} id - 提示词集ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  partialUpdate(id, data) {
    return apiClient({
      url: `/prompts/sets/${id}/`,
      method: 'patch',
      data,
    });
  },

  /**
   * 删除提示词集
   * @param {String} id - 提示词集ID
   * @returns {Promise}
   */
  delete(id) {
    return apiClient({
      url: `/prompts/sets/${id}/`,
      method: 'delete',
    });
  },

  /**
   * 克隆提示词集
   * @param {String} id - 源提示词集ID
   * @param {String} name - 新提示词集名称
   * @returns {Promise}
   */
  clone(id, name) {
    return apiClient({
      url: `/prompts/sets/${id}/clone/`,
      method: 'post',
      data: { name },
    });
  },

  /**
   * 设置为默认提示词集
   * @param {String} id - 提示词集ID
   * @returns {Promise}
   */
  setDefault(id) {
    return apiClient({
      url: `/prompts/sets/${id}/set_default/`,
      method: 'post',
    });
  },

  /**
   * 获取默认提示词集
   * @returns {Promise}
   */
  getDefault() {
    return apiClient({
      url: '/prompts/sets/default/',
      method: 'get',
    });
  },
};

/**
 * 提示词模板API
 */
export const promptTemplateAPI = {
  /**
   * 获取提示词模板列表
   * @param {Object} params - 查询参数 {template_set, stage_type, is_active, page, page_size}
   * @returns {Promise}
   */
  getList(params = {}) {
    return apiClient({
      url: '/prompts/templates/',
      method: 'get',
      params,
    });
  },

  /**
   * 获取提示词模板详情
   * @param {String} id - 模板ID
   * @returns {Promise}
   */
  getDetail(id) {
    return apiClient({
      url: `/prompts/templates/${id}/`,
      method: 'get',
    });
  },

  /**
   * 创建提示词模板
   * @param {Object} data - {template_set, stage_type, template_content, variables, is_active}
   * @returns {Promise}
   */
  create(data) {
    return apiClient({
      url: '/prompts/templates/',
      method: 'post',
      data,
    });
  },

  /**
   * 更新提示词模板
   * @param {String} id - 模板ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  update(id, data) {
    return apiClient({
      url: `/prompts/templates/${id}/`,
      method: 'put',
      data,
    });
  },

  /**
   * 部分更新提示词模板
   * @param {String} id - 模板ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  partialUpdate(id, data) {
    return apiClient({
      url: `/prompts/templates/${id}/`,
      method: 'patch',
      data,
    });
  },

  /**
   * 删除提示词模板
   * @param {String} id - 模板ID
   * @returns {Promise}
   */
  delete(id) {
    return apiClient({
      url: `/prompts/templates/${id}/`,
      method: 'delete',
    });
  },

  /**
   * 创建新版本
   * @param {String} id - 原模板ID
   * @param {Object} data - {template_content, variables}
   * @returns {Promise}
   */
  createVersion(id, data) {
    return apiClient({
      url: `/prompts/templates/${id}/create_version/`,
      method: 'post',
      data,
    });
  },

  /**
   * 获取版本历史
   * @param {String} id - 模板ID
   * @returns {Promise}
   */
  getVersions(id) {
    return apiClient({
      url: `/prompts/templates/${id}/versions/`,
      method: 'get',
    });
  },

  /**
   * 验证模板语法
   * @param {String} id - 模板ID
   * @param {String} templateContent - 模板内容
   * @returns {Promise}
   */
  validate(id, templateContent) {
    return apiClient({
      url: `/prompts/templates/${id}/validate/`,
      method: 'post',
      data: { template_content: templateContent },
    });
  },

  /**
   * 预览模板渲染结果
   * @param {String} id - 模板ID
   * @param {Object} variables - 变量值 {topic: "科幻", style: "赛博朋克"}
   * @returns {Promise}
   */
  preview(id, variables) {
    return apiClient({
      url: `/prompts/templates/${id}/preview/`,
      method: 'post',
      data: { variables },
    });
  },

  /**
   * AI评估提示词效果
   * @param {String} id - 模板ID
   * @returns {Promise}
   */
  evaluate(id) {
    return apiClient({
      url: `/prompts/templates/${id}/evaluate/`,
      method: 'post',
    });
  },
};

/**
 * 阶段类型配置
 */
export const STAGE_TYPES = [
  { value: 'rewrite', label: '文案改写' },
  { value: 'storyboard', label: '分镜生成' },
  { value: 'image_generation', label: '文生图' },
  { value: 'camera_movement', label: '运镜生成' },
  { value: 'video_generation', label: '图生视频' },
];

/**
 * 变量类型配置
 */
export const VARIABLE_TYPES = [
  { value: 'string', label: '字符串' },
  { value: 'int', label: '整数' },
  { value: 'float', label: '浮点数' },
  { value: 'bool', label: '布尔值' },
  { value: 'list', label: '列表' },
  { value: 'dict', label: '字典' },
];

/**
 * 全局变量API
 */
export const globalVariableAPI = {
  /**
   * 获取全局变量列表
   * @param {Object} params - 查询参数 {scope, group, variable_type, is_active, search, page, page_size}
   * @returns {Promise}
   */
  getList(params = {}) {
    return apiClient({
      url: '/prompts/variables/',
      method: 'get',
      params,
    });
  },

  /**
   * 获取全局变量详情
   * @param {String} id - 变量ID
   * @returns {Promise}
   */
  getDetail(id) {
    return apiClient({
      url: `/prompts/variables/${id}/`,
      method: 'get',
    });
  },

  /**
   * 创建全局变量
   * @param {Object} data - {key, value, variable_type, scope, group, description, is_active}
   * @returns {Promise}
   */
  create(data) {
    return apiClient({
      url: '/prompts/variables/',
      method: 'post',
      data,
    });
  },

  /**
   * 更新全局变量
   * @param {String} id - 变量ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  update(id, data) {
    return apiClient({
      url: `/prompts/variables/${id}/`,
      method: 'put',
      data,
    });
  },

  /**
   * 部分更新全局变量
   * @param {String} id - 变量ID
   * @param {Object} data - 更新数据
   * @returns {Promise}
   */
  partialUpdate(id, data) {
    return apiClient({
      url: `/prompts/variables/${id}/`,
      method: 'patch',
      data,
    });
  },

  /**
   * 删除全局变量
   * @param {String} id - 变量ID
   * @returns {Promise}
   */
  delete(id) {
    return apiClient({
      url: `/prompts/variables/${id}/`,
      method: 'delete',
    });
  },

  /**
   * 获取所有变量分组
   * @returns {Promise}
   */
  getGroups() {
    return apiClient({
      url: '/prompts/variables/groups/',
      method: 'get',
    });
  },

  /**
   * 获取可用于模板渲染的变量字典
   * @param {Boolean} includeSystem - 是否包含系统级变量
   * @returns {Promise}
   */
  getForTemplate(includeSystem = true) {
    return apiClient({
      url: '/prompts/variables/for_template/',
      method: 'get',
      params: { include_system: includeSystem },
    });
  },

  /**
   * 批量创建/更新变量
   * @param {Array} variables - 变量列表 [{key, value, variable_type, scope, group, description}, ...]
   * @returns {Promise}
   */
  batchCreate(variables) {
    return apiClient({
      url: '/prompts/variables/batch_create/',
      method: 'post',
      data: { variables },
    });
  },

  /**
   * 验证变量键是否可用
   * @param {String} key - 变量键
   * @param {String} scope - 作用域 (user/system)
   * @returns {Promise}
   */
  validateKey(key, scope = 'user') {
    return apiClient({
      url: '/prompts/variables/validate_key/',
      method: 'post',
      data: { key, scope },
    });
  },
};

/**
 * 全局变量类型配置
 */
export const GLOBAL_VARIABLE_TYPES = [
  { value: 'string', label: '字符串' },
  { value: 'number', label: '数字' },
  { value: 'boolean', label: '布尔值' },
  { value: 'json', label: 'JSON对象' },
];

/**
 * 全局变量作用域配置
 */
export const GLOBAL_VARIABLE_SCOPES = [
  { value: 'user', label: '用户级' },
  { value: 'system', label: '系统级' },
];
