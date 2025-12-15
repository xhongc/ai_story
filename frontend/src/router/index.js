import Vue from 'vue';
import VueRouter from 'vue-router';
import store from '@/store';

Vue.use(VueRouter);

const routes = [
  {
    path: '/',
    redirect: '/projects',
  },
  // 认证相关路由
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: {
      title: '登录',
      requiresGuest: true, // 需要未登录状态
    },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: {
      title: '注册',
      requiresGuest: true,
    },
  },
  // 项目管理路由
  {
    path: '/projects',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ProjectList',
        component: () => import('@/views/projects/ProjectList.vue'),
        meta: { title: '项目列表' },
      },
      {
        path: 'create',
        name: 'ProjectCreate',
        component: () => import('@/views/projects/ProjectCreate.vue'),
        meta: { title: '创建项目' },
      },
      {
        path: ':id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetail.vue'),
        meta: { title: '项目详情' },
      },
      {
        path: ':id/edit',
        name: 'ProjectEdit',
        component: () => import('@/views/projects/ProjectEdit.vue'),
        meta: { title: '编辑项目' },
      },
    ],
  },
  // 提示词管理路由
  {
    path: '/prompts',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'PromptList',
        component: () => import('@/views/prompts/PromptList.vue'),
        meta: { title: '提示词管理' },
      },
      {
        path: 'sets/create',
        name: 'PromptSetCreate',
        component: () => import('@/views/prompts/PromptSetForm.vue'),
        meta: { title: '创建提示词集' },
      },
      {
        path: 'sets/:id',
        name: 'PromptSetDetail',
        component: () => import('@/views/prompts/PromptSetDetail.vue'),
        meta: { title: '提示词集详情' },
      },
      {
        path: 'sets/:id/edit',
        name: 'PromptSetEdit',
        component: () => import('@/views/prompts/PromptSetForm.vue'),
        meta: { title: '编辑提示词集' },
      },
      {
        path: 'templates/create',
        name: 'PromptTemplateCreate',
        component: () => import('@/views/prompts/PromptTemplateEditor.vue'),
        meta: { title: '创建提示词模板' },
      },
      {
        path: 'templates/:id/edit',
        name: 'PromptTemplateEdit',
        component: () => import('@/views/prompts/PromptTemplateEditor.vue'),
        meta: { title: '编辑提示词模板' },
      },
      {
        path: 'variables',
        name: 'GlobalVariableList',
        component: () => import('@/views/prompts/GlobalVariableList.vue'),
        meta: { title: '全局变量管理' },
      },
    ],
  },
  // 模型管理路由
  {
    path: '/models',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ModelList',
        component: () => import('@/views/models/ModelList.vue'),
        meta: { title: '模型管理' },
      },
      {
        path: 'create',
        name: 'model-create',
        component: () => import('@/views/models/ModelForm.vue'),
        meta: { title: '添加模型' },
      },
      {
        path: ':id/edit',
        name: 'model-edit',
        component: () => import('@/views/models/ModelForm.vue'),
        meta: { title: '编辑模型' },
      },
    ],
  },
  // 404页面
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' },
  },
  {
    path: '*',
    redirect: '/404',
  },
];

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { x: 0, y: 0 };
  },
});

// 全局前置守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - AI Story生成系统`;
  }

  // 获取认证状态
  const isAuthenticated = store.getters['auth/isAuthenticated'];

  // 检查路由是否需要认证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  // 检查路由是否需要访客状态(未登录)
  const requiresGuest = to.matched.some(record => record.meta.requiresGuest);

  if (requiresAuth && !isAuthenticated) {
    // 需要认证但未登录,跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath }, // 记录原本要访问的页面
    });
  } else if (requiresGuest && isAuthenticated) {
    // 需要访客状态但已登录,跳转到首页
    next('/projects');
  } else {
    // 正常访问
    next();
  }
});

export default router;
