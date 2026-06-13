import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/RegisterView.vue'),
      meta: { guest: true },
    },
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('@/views/auth/VerifyEmailView.vue'),
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/views/auth/ResetPasswordView.vue'),
    },
    {
      path: '/quick-reduce',
      name: 'quick-reduce',
      component: () => import('@/views/QuickReduceView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/prompts',
      name: 'prompts',
      component: () => import('@/views/prompt/PromptManagerView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/admin/AdminSettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/documents',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'upload',
          redirect: { name: 'history' },
        },
        {
          path: ':id/reduce',
          name: 'reduce',
          component: () => import('@/views/document/ReductionView.vue'),
          props: true,
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/document/HistoryView.vue'),
        },
      ],
    },
    // 捕获外部注入的未知路径（如浏览器扩展的 JSONP 回调），避免 Vue Router 警告
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

router.beforeEach(async (to, from) => {
  const auth = useAuthStore()

  // 确保认证状态已从 localStorage 恢复（页面刷新后第一次导航）
  // init() 是幂等的 — 如果已初始化，立即返回
  if (!auth.initialized) {
    await auth.init()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.guest && auth.isAuthenticated) {
    return { name: 'history' }
  }
  // 不返回任何值即允许导航
})

export default router
