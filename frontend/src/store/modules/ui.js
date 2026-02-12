/**
 * UI状态管理模块
 * 管理界面相关状态,如侧边栏折叠状态等
 */

// 从localStorage获取保存的侧边栏状态
const getSavedSidebarState = () => {
  try {
    const saved = localStorage.getItem('sidebar_collapsed');
    return saved === 'true';
  } catch (error) {
    return false;
  }
};

// 从localStorage获取保存的主题
const getSavedTheme = () => {
  try {
    const saved = localStorage.getItem('ui_theme');
    return saved === 'dark' ? 'dark' : 'light';
  } catch (error) {
    return 'light';
  }
};

const state = {
  // 侧边栏是否折叠
  sidebarCollapsed: getSavedSidebarState(),
  // 主题(light | dark)
  theme: getSavedTheme(),
};

const mutations = {
  /**
   * 切换侧边栏折叠状态
   */
  TOGGLE_SIDEBAR(state) {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    // 持久化到localStorage
    try {
      localStorage.setItem('sidebar_collapsed', state.sidebarCollapsed.toString());
    } catch (error) {
      console.error('保存侧边栏状态失败:', error);
    }
  },

  /**
   * 设置侧边栏折叠状态
   */
  SET_SIDEBAR_COLLAPSED(state, collapsed) {
    state.sidebarCollapsed = collapsed;
    // 持久化到localStorage
    try {
      localStorage.setItem('sidebar_collapsed', collapsed.toString());
    } catch (error) {
      console.error('保存侧边栏状态失败:', error);
    }
  },

  /**
   * 设置主题
   */
  SET_THEME(state, theme) {
    state.theme = theme === 'dark' ? 'dark' : 'light';
    try {
      localStorage.setItem('ui_theme', state.theme);
    } catch (error) {
      console.error('保存主题失败:', error);
    }
  },
};

const actions = {
  /**
   * 切换侧边栏折叠状态
   */
  toggleSidebar({ commit }) {
    commit('TOGGLE_SIDEBAR');
  },

  /**
   * 设置侧边栏折叠状态
   */
  setSidebarCollapsed({ commit }, collapsed) {
    commit('SET_SIDEBAR_COLLAPSED', collapsed);
  },

  /**
   * 切换主题
   */
  toggleTheme({ commit, state }) {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    commit('SET_THEME', nextTheme);
  },

  /**
   * 设置主题
   */
  setTheme({ commit }, theme) {
    commit('SET_THEME', theme);
  },
};

const getters = {
  /**
   * 获取侧边栏折叠状态
   */
  sidebarCollapsed: (state) => state.sidebarCollapsed,
  /**
   * 获取主题
   */
  theme: (state) => state.theme,
  /**
   * 是否暗色主题
   */
  isDark: (state) => state.theme === 'dark',
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
};
