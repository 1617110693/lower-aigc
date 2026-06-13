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
    },
    {
      path: '/documents',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'upload',
          name: 'upload',
          component: () => import('@/views/document/UploadView.vue'),
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
  ],
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && auth.isAuthenticated) {
    next({ name: 'upload' })
  } else {
    next()
  }
})

export default router
