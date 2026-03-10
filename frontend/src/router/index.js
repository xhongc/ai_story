import Vue from 'vue';
import VueRouter from 'vue-router';
import store from '@/store';

Vue.use(VueRouter);

const routes = [
  {
    path: '/',
    redirect: '/series',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: {
      title: '登录',
      requiresGuest: true,
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
  {
    path: '/series',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'SeriesList',
        component: () => import('@/views/projects/SeriesList.vue'),
        meta: { title: '作品列表' },
      },
      {
        path: ':id',
        name: 'SeriesDetail',
        component: () => import('@/views/projects/SeriesDetail.vue'),
        meta: { title: '作品详情' },
      },
    ],
  },
  {
    path: '/projects',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'ProjectList',
        component: () => import('@/views/projects/ProjectList.vue'),
        meta: { title: '分集列表' },
      },
      {
        path: 'create',
        name: 'ProjectCreate',
        component: () => import('@/views/projects/ProjectCreate.vue'),
        meta: { title: '创建分集' },
      },
      {
        path: ':id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetail.vue'),
        meta: { title: '分集详情' },
      },
      {
        path: ':id/edit',
        name: 'ProjectEdit',
        component: () => import('@/views/projects/ProjectEdit.vue'),
        meta: { title: '编辑分集' },
      },
    ],
  },
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
    ],
  },
  {
    path: '/assets',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'AssetList',
        component: () => import('@/views/assets/AssetList.vue'),
        meta: { title: '资产管理' },
      },
      {
        path: 'new',
        name: 'AssetCreate',
        component: () => import('@/views/assets/AssetForm.vue'),
        meta: { title: '新建资产' },
      },
      {
        path: ':id',
        name: 'AssetDetail',
        component: () => import('@/views/assets/AssetForm.vue'),
        meta: { title: '编辑资产' },
      },
    ],
  },
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

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - AI Story生成系统`;
  }

  const isAuthenticated = store.getters['auth/isAuthenticated'];
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const requiresGuest = to.matched.some(record => record.meta.requiresGuest);

  if (requiresAuth && !isAuthenticated) {
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    });
  } else if (requiresGuest && isAuthenticated) {
    next('/series');
  } else {
    next();
  }
});

export default router;
