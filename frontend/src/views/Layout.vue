<template>
  <div class="drawer lg:drawer-open">
    <!-- 移动端抽屉切换 -->
    <input id="main-drawer" type="checkbox" class="drawer-toggle" />

    <!-- 主内容区 -->
    <div class="drawer-content flex flex-col">
      <!-- 顶部导航栏 -->
      <header class="navbar bg-base-100 border-b border-base-300 px-4 lg:px-6">
        <!-- 桌面端折叠/展开按钮 -->
        <div class="flex-none hidden lg:block">
          <button
            class="btn btn-square btn-ghost"
            @click="toggleSidebar"
            :title="sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="w-5 h-5 transition-transform duration-300"
              :class="{ 'rotate-180': !sidebarCollapsed }"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
              />
            </svg>
          </button>
        </div>

        <!-- 移动端菜单按钮 -->
        <div class="flex-none lg:hidden">
          <label for="main-drawer" class="btn btn-square btn-ghost">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              class="inline-block w-5 h-5 stroke-current"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              ></path>
            </svg>
          </label>
        </div>

        <!-- 面包屑导航 -->
        <div class="flex-1">
          <div class="text-sm breadcrumbs">
            <ul>
              <li v-for="(item, index) in breadcrumbs" :key="index">
                <router-link :to="item.path">{{ item.label }}</router-link>
              </li>
            </ul>
          </div>
        </div>

        <!-- 右侧操作按钮 -->
        <div class="flex-none gap-2">
          <button class="btn btn-ghost btn-circle" @click="handleRefresh">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="w-5 h-5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
          </button>

          <!-- 用户菜单 -->
          <div class="dropdown dropdown-end">
            <label tabindex="0" class="btn btn-ghost btn-circle avatar placeholder">
              <div class="bg-neutral-focus text-neutral-content rounded-full w-10">
                <span class="text-xl">{{ userInitial }}</span>
              </div>
            </label>
            <ul
              tabindex="0"
              class="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52"
            >
              <li class="menu-title">
                <span>{{ username }}</span>
              </li>
              <li>
                <a @click="handleProfile">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
                    />
                  </svg>
                  个人资料
                </a>
              </li>
              <li>
                <a @click="handleLogout">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"
                    />
                  </svg>
                  退出登录
                </a>
              </li>
            </ul>
          </div>
        </div>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 overflow-y-auto p-6 bg-base-200">
        <router-view />
      </main>
    </div>

    <!-- 侧边栏 -->
    <div class="drawer-side z-40">
      <label for="main-drawer" class="drawer-overlay"></label>
      <aside
        class="bg-base-100 text-base-content min-h-full border-r border-base-300 transition-all duration-300 ease-in-out overflow-hidden"
        :class="sidebarCollapsed ? 'w-16' : 'w-64'"
      >
        <!-- Logo -->
        <div
          class="sticky top-0 z-20 bg-base-100 bg-opacity-90 backdrop-blur py-4 border-b border-base-300 transition-all duration-300"
          :class="sidebarCollapsed ? 'px-2' : 'px-6'"
        >
          <h1
            class="text-xl font-bold transition-all duration-300 overflow-hidden whitespace-nowrap"
            :class="sidebarCollapsed ? 'text-center text-sm' : ''"
          >
            {{ sidebarCollapsed ? 'AI' : 'AI Story' }}
          </h1>
        </div>

        <!-- 导航菜单 -->
        <ul class="menu p-2 w-full" :class="sidebarCollapsed ? 'menu-compact' : ''">
          <li>
            <router-link
              to="/projects"
              :class="{ 'active': activeMenu === '/projects' }"
              class="flex items-center gap-3 tooltip tooltip-right"
              :data-tip="sidebarCollapsed ? '项目管理' : ''"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-5 h-5 flex-shrink-0"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
                />
              </svg>
              <span
                v-show="!sidebarCollapsed"
                class="transition-opacity duration-300"
                :class="sidebarCollapsed ? 'opacity-0' : 'opacity-100'"
              >项目管理</span>
            </router-link>
          </li>
          <li>
            <router-link
              to="/prompts"
              :class="{ 'active': activeMenu === '/prompts' }"
              class="flex items-center gap-3 tooltip tooltip-right"
              :data-tip="sidebarCollapsed ? '提示词管理' : ''"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-5 h-5 flex-shrink-0"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
                />
              </svg>
              <span
                v-show="!sidebarCollapsed"
                class="transition-opacity duration-300"
                :class="sidebarCollapsed ? 'opacity-0' : 'opacity-100'"
              >提示词管理</span>
            </router-link>
          </li>
          <li>
            <router-link
              to="/prompts/variables"
              :class="{ 'active': activeMenu === '/prompts/variables' }"
              class="flex items-center gap-3 tooltip tooltip-right"
              :data-tip="sidebarCollapsed ? '全局变量' : ''"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-5 h-5 flex-shrink-0"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                />
              </svg>
              <span
                v-show="!sidebarCollapsed"
                class="transition-opacity duration-300"
                :class="sidebarCollapsed ? 'opacity-0' : 'opacity-100'"
              >全局变量</span>
            </router-link>
          </li>
          <li>
            <router-link
              to="/models"
              :class="{ 'active': activeMenu === '/models' }"
              class="flex items-center gap-3 tooltip tooltip-right"
              :data-tip="sidebarCollapsed ? '模型管理' : ''"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
                class="w-5 h-5 flex-shrink-0"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z"
                />
              </svg>
              <span
                v-show="!sidebarCollapsed"
                class="transition-opacity duration-300"
                :class="sidebarCollapsed ? 'opacity-0' : 'opacity-100'"
              >模型管理</span>
            </router-link>
          </li>
        </ul>
      </aside>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'Layout',
  computed: {
    ...mapGetters('auth', ['username', 'user']),
    ...mapGetters('ui', ['sidebarCollapsed']),
    activeMenu() {
      const route = this.$route;
      const { path } = route;
      return path;
    },
    breadcrumbs() {
      const route = this.$route;
      const breadcrumbs = [];

      if (route.matched && route.matched.length > 0) {
        route.matched.forEach((item) => {
          if (item.meta && item.meta.title) {
            breadcrumbs.push({
              label: item.meta.title,
              path: item.path,
            });
          }
        });
      }

      return breadcrumbs;
    },
    userInitial() {
      // 获取用户名首字母作为头像
      return this.username ? this.username.charAt(0).toUpperCase() : 'U';
    },
  },
  methods: {
    ...mapActions('auth', ['logout']),
    ...mapActions('ui', ['toggleSidebar']),
    handleRefresh() {
      this.$router.go(0);
    },
    handleProfile() {
      // TODO: 跳转到个人资料页面
      console.log('跳转到个人资料页面');
    },
    async handleLogout() {
      try {
        await this.logout();
        this.$router.push('/login');
      } catch (error) {
        console.error('登出失败:', error);
      }
    },
  },
};
</script>

<style scoped>
/* 自定义样式可以在这里添加 */
</style>
