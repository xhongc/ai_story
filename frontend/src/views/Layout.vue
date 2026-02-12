<template>
  <div
    class="layout-shell"
    :class="{ 'rail-collapsed': sidebarCollapsed, 'theme-dark': isDark }"
  >
    <!-- 移动端抽屉切换 -->
    <input id="main-drawer" type="checkbox" class="drawer-toggle" />

    <!-- 主内容区 -->
    <div class="drawer-content flex flex-col">
      <!-- 顶部导航栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <!-- 移动端菜单按钮 -->
          <div class="flex-none lg:hidden">
            <label for="main-drawer" class="icon-button" aria-label="打开导航">
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

          <div class="brand-chip">AI Story</div>

          <!-- 面包屑导航 -->
          <div class="text-sm breadcrumbs">
            <ul>
              <li v-for="(item, index) in breadcrumbs" :key="index">
                <router-link :to="item.path">{{ item.label }}</router-link>
              </li>
            </ul>
          </div>
        </div>

        <!-- 右侧操作按钮 -->
        <div class="topbar-actions">
          <button
            class="icon-button"
            @click="handleThemeToggle"
            :aria-label="isDark ? '切换到浅色主题' : '切换到深色主题'"
            :title="isDark ? '切换到浅色主题' : '切换到深色主题'"
          >
            <svg
              v-if="isDark"
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
                d="M12 3v2.25m0 13.5V21m-6.364-2.636l1.591-1.591m9.546-9.546l1.591-1.591M3 12h2.25m13.5 0H21m-2.636 6.364l-1.591-1.591m-9.546-9.546l-1.591-1.591M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <svg
              v-else
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
                d="M21.752 15.002A9.718 9.718 0 0112 21.75a9.75 9.75 0 01-9.75-9.75 9.718 9.718 0 016.748-9.252.75.75 0 01.96.93 7.5 7.5 0 009.364 9.364.75.75 0 01.93.96z"
              />
            </svg>
          </button>
          <button class="icon-button" @click="handleRefresh" aria-label="刷新">
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
            <label tabindex="0" class="icon-button avatar placeholder" aria-label="用户菜单">
              <div class="avatar-orb">
                <span class="text-lg">{{ userInitial }}</span>
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
      <main class="main-surface">
        <router-view />
      </main>
    </div>

    <!-- 移动端侧边栏 -->
    <div class="drawer-side z-40 lg:hidden">
      <label for="main-drawer" class="drawer-overlay"></label>
      <aside class="mobile-drawer">
        <div class="mobile-header">AI Story</div>
        <ul class="menu p-3">
          <li>
            <router-link
              to="/projects"
              :class="{ 'active': activeMenu === '/projects' }"
            >项目管理</router-link>
          </li>
          <li>
            <router-link
              to="/prompts"
              :class="{ 'active': activeMenu === '/prompts' }"
            >提示词管理</router-link>
          </li>
          <li>
            <router-link
              to="/assets"
              :class="{ 'active': activeMenu === '/assets' || activeMenu.startsWith('/assets/') }"
            >资产管理</router-link>
          </li>
          <li>
            <router-link
              to="/models"
              :class="{ 'active': activeMenu === '/models' }"
            >模型管理</router-link>
          </li>
        </ul>
      </aside>
    </div>

    <div class="rail-hover-zone hidden lg:block" aria-hidden="true"></div>

    <!-- 浮动侧边导航栏（桌面端） -->
    <nav class="floating-rail hidden lg:flex" :class="{ 'is-collapsed': sidebarCollapsed }">
      <div class="rail-orb">
        <span>AI</span>
      </div>
      <ul class="rail-menu">
        <li>
          <router-link
            to="/projects"
            class="rail-item"
            :class="{ 'is-active': activeMenu === '/projects' }"
            :data-tip="sidebarCollapsed ? '项目管理' : ''"
            style="--rail-index: 0"
          >
            <span class="rail-icon">
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
                  d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
                />
              </svg>
            </span>
            <span class="rail-label">项目管理</span>
          </router-link>
        </li>
        <li>
          <router-link
            to="/prompts"
            class="rail-item"
            :class="{ 'is-active': activeMenu === '/prompts' }"
            :data-tip="sidebarCollapsed ? '提示词管理' : ''"
            style="--rail-index: 1"
          >
            <span class="rail-icon">
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
                  d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"
                />
              </svg>
            </span>
            <span class="rail-label">提示词管理</span>
          </router-link>
        </li>
        <li>
          <router-link
            to="/assets"
            class="rail-item"
            :class="{ 'is-active': activeMenu === '/assets' || activeMenu.startsWith('/assets/') }"
            :data-tip="sidebarCollapsed ? '资产管理' : ''"
            style="--rail-index: 2"
          >
            <span class="rail-icon">
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
                  d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
              </svg>
            </span>
            <span class="rail-label">资产管理</span>
          </router-link>
        </li>
        <li>
          <router-link
            to="/models"
            class="rail-item"
            :class="{ 'is-active': activeMenu === '/models' }"
            :data-tip="sidebarCollapsed ? '模型管理' : ''"
            style="--rail-index: 3"
          >
            <span class="rail-icon">
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
                  d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z"
                />
              </svg>
            </span>
            <span class="rail-label">模型管理</span>
          </router-link>
        </li>
      </ul>
      <button
        class="rail-toggle"
        @click="toggleSidebar"
        :aria-label="sidebarCollapsed ? '展开导航栏' : '折叠导航栏'"
        :title="sidebarCollapsed ? '展开导航栏' : '折叠导航栏'"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
          class="w-4 h-4 transition-transform duration-300"
          :class="{ 'rotate-180': sidebarCollapsed }"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15.75 19.5L8.25 12l7.5-7.5"
          />
        </svg>
      </button>
    </nav>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  name: 'Layout',
  computed: {
    ...mapGetters('auth', ['username', 'user']),
    ...mapGetters('ui', ['sidebarCollapsed', 'isDark']),
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
    ...mapActions('ui', ['toggleSidebar', 'toggleTheme']),
    handleRefresh() {
      this.$router.go(0);
    },
    handleThemeToggle() {
      this.toggleTheme();
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
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=Noto+Sans+SC:wght@400;600&display=swap');

.layout-shell {
  --rail-width: 220px;
  --rail-collapsed-width: 76px;
  --rail-gap: 28px;
  --rail-surface: rgba(255, 255, 255, 0.92);
  --rail-border: rgba(15, 23, 42, 0.08);
  --accent: #14b8a6;
  --accent-soft: rgba(20, 184, 166, 0.18);
  --ink: #0f172a;
  --muted: #64748b;
  --surface: rgba(255, 255, 255, 0.9);
  --surface-strong: #ffffff;
  font-family: 'Space Grotesk', 'Noto Sans SC', sans-serif;
  min-height: 100vh;
  color: var(--ink);
  background: radial-gradient(circle at 10% 10%, rgba(148, 163, 184, 0.2), transparent 40%),
    radial-gradient(circle at 90% 15%, rgba(20, 184, 166, 0.16), transparent 45%),
    linear-gradient(120deg, #f8fafc 0%, #e2e8f0 100%);
  position: relative;
  transition: color 200ms ease, background 260ms ease;
}

.layout-shell.theme-dark {
  --rail-surface: rgba(15, 23, 42, 0.9);
  --rail-border: rgba(148, 163, 184, 0.2);
  --accent: #5eead4;
  --accent-soft: rgba(94, 234, 212, 0.18);
  --ink: #e2e8f0;
  --muted: #94a3b8;
  --surface: rgba(15, 23, 42, 0.88);
  --surface-strong: rgba(15, 23, 42, 0.96);
  background: radial-gradient(circle at 12% 15%, rgba(94, 234, 212, 0.16), transparent 45%),
    radial-gradient(circle at 88% 18%, rgba(59, 130, 246, 0.2), transparent 48%),
    linear-gradient(120deg, #0b1120 0%, #0f172a 55%, #111827 100%);
}

.layout-shell.theme-dark::before {
  background-image: linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  opacity: 0.25;
}

.layout-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(148, 163, 184, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.12) 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.4;
  pointer-events: none;
}

.drawer-content {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  height: 100vh;
  transition: padding-left 260ms ease;
}

@media (min-width: 1024px) {
  .drawer-content {
    padding-left: calc(var(--rail-collapsed-width) + var(--rail-gap));
  }

  .layout-shell.rail-collapsed .drawer-content {
    padding-left: 0;
  }
}

.layout-shell > .drawer-toggle,
.layout-shell > .drawer-side {
  display: none;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  margin: 20px 20px 0;
  border-radius: 18px;
  background: var(--surface);
  border: 1px solid rgba(148, 163, 184, 0.25);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(14px);
  animation: surface-rise 520ms ease;
}

.layout-shell.theme-dark .topbar {
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 18px 45px rgba(3, 7, 18, 0.45);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-chip {
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  background: rgba(15, 23, 42, 0.08);
  color: var(--ink);
}

.layout-shell.theme-dark .brand-chip {
  background: rgba(148, 163, 184, 0.18);
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.72);
  color: var(--ink);
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.layout-shell.theme-dark .icon-button {
  border-color: rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.85);
}

.icon-button:hover {
  transform: translateY(-1px);
  border-color: rgba(20, 184, 166, 0.6);
  box-shadow: 0 10px 20px rgba(20, 184, 166, 0.2);
}

.avatar-orb {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.9), rgba(13, 148, 136, 0.85));
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.main-surface {
  flex: 1;
  margin: 18px 20px 24px;
  padding: 22px;
  border-radius: 24px;
  background: var(--surface);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.12);
  overflow: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.layout-shell.theme-dark .main-surface {
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 24px 60px rgba(3, 7, 18, 0.5);
}

.main-surface > .project-detail {
  flex: 1;
  min-height: 0;
}

.mobile-drawer {
  background: #f8fafc;
  color: #0f172a;
  min-height: 100vh;
  width: 78vw;
  max-width: 320px;
  padding-top: 16px;
}

.layout-shell.theme-dark .mobile-drawer {
  background: #0f172a;
  color: #e2e8f0;
}

.mobile-header {
  padding: 12px 18px;
  font-weight: 600;
  letter-spacing: 0.6px;
  color: #0f172a;
}

.layout-shell.theme-dark .mobile-header {
  color: #e2e8f0;
}

.floating-rail {
  position: fixed;
  top: 50%;
  left: 22px;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  width: 76px;
  padding: 16px 10px 18px;
  border-radius: 999px;
  background: var(--rail-surface);
  border: 1px solid var(--rail-border);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(18px);
  z-index: 20;
  animation: rail-fade 520ms ease;
  transition: transform 260ms ease, opacity 260ms ease;
}

.layout-shell.theme-dark .floating-rail {
  box-shadow: 0 22px 60px rgba(2, 6, 23, 0.55);
}

.rail-hover-zone {
  position: fixed;
  top: 0;
  left: 0;
  width: 32px;
  height: 100vh;
  z-index: 19;
  opacity: 0;
  pointer-events: none;
}

.layout-shell.rail-collapsed .rail-hover-zone {
  pointer-events: auto;
}

.layout-shell.rail-collapsed .floating-rail {
  transform: translate(-140%, -50%);
  opacity: 0;
  pointer-events: none;
}

.layout-shell.rail-collapsed .rail-hover-zone:hover ~ .floating-rail,
.layout-shell.rail-collapsed .floating-rail:hover {
  transform: translate(0, -50%);
  opacity: 1;
  pointer-events: auto;
}

.rail-orb {
  width: 46px;
  height: 46px;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(135deg, rgba(20, 184, 166, 0.95), rgba(13, 148, 136, 0.85));
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.35);
}

.rail-menu {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.rail-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  width: 100%;
  padding: 10px;
  border-radius: 18px;
  color: #0f172a;
  background: transparent;
  transition: all 180ms ease;
  animation: rail-item 400ms ease;
  animation-delay: calc(var(--rail-index, 0) * 70ms);
  animation-fill-mode: both;
  position: relative;
}

.layout-shell.theme-dark .rail-item {
  color: var(--ink);
}

.rail-item:hover {
  background: rgba(15, 23, 42, 0.06);
  transform: translateX(2px);
}

.layout-shell.theme-dark .rail-item:hover {
  background: rgba(148, 163, 184, 0.14);
}

.rail-item.is-active {
  background: rgba(20, 184, 166, 0.16);
  color: #0f172a;
  box-shadow: inset 0 0 0 1px rgba(20, 184, 166, 0.4);
}

.layout-shell.theme-dark .rail-item.is-active {
  background: rgba(94, 234, 212, 0.2);
  color: var(--ink);
  box-shadow: inset 0 0 0 1px rgba(94, 234, 212, 0.5);
}

.rail-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.06);
}

.layout-shell.theme-dark .rail-icon {
  background: rgba(148, 163, 184, 0.16);
}

.rail-label {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  transform: translate(-4px, -50%);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3px;
  white-space: nowrap;
  color: #0f172a;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}

.layout-shell.theme-dark .rail-label {
  color: var(--ink);
  background: rgba(15, 23, 42, 0.95);
  border-color: rgba(148, 163, 184, 0.2);
  box-shadow: 0 12px 28px rgba(2, 6, 23, 0.5);
}

.rail-item:hover .rail-label {
  opacity: 1;
  transform: translate(0, -50%);
}

.rail-toggle {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.95);
  color: #0f172a;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 160ms ease, border-color 160ms ease;
}

.layout-shell.theme-dark .rail-toggle {
  border-color: rgba(148, 163, 184, 0.2);
  background: rgba(15, 23, 42, 0.9);
  color: var(--ink);
}

.rail-toggle:hover {
  transform: translateY(-2px);
  border-color: rgba(20, 184, 166, 0.6);
}

@media (max-width: 1023px) {
  .layout-shell > .drawer-toggle,
  .layout-shell > .drawer-side {
    display: block;
  }

  .topbar {
    margin: 16px 16px 0;
  }

  .main-surface {
    margin: 16px;
    padding: 18px;
  }
}

@keyframes rail-fade {
  from {
    opacity: 0;
    transform: translate(-12px, -50%);
  }
  to {
    opacity: 1;
    transform: translate(0, -50%);
  }
}

@keyframes rail-item {
  from {
    opacity: 0;
    transform: translateX(-8px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes surface-rise {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
