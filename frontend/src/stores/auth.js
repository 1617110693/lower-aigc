import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getMe, verifyEmail, forgotPassword, resetPassword } from '@/api/auth'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!user.value)
  const userEmail = computed(() => user.value?.email)

  async function init() {
    const token = localStorage.getItem('token')
    if (!token) return
    try {
      const res = await getMe()
      user.value = res.data
    } catch {
      localStorage.removeItem('token')
    }
  }

  async function login(email, password) {
    loading.value = true
    try {
      const res = await apiLogin(email, password)
      localStorage.setItem('token', res.data.access_token)
      user.value = res.data.user
      ElMessage.success('Login successful')
      return true
    } finally {
      loading.value = false
    }
  }

  async function register(email, password) {
    loading.value = true
    try {
      await apiRegister(email, password)
      ElMessage.success('Registration successful. Please check your email.')
      return true
    } finally {
      loading.value = false
    }
  }

  async function verify(token) {
    loading.value = true
    try {
      await verifyEmail(token)
      ElMessage.success('Email verified successfully')
      return true
    } finally {
      loading.value = false
    }
  }

  async function forgotPwd(email) {
    loading.value = true
    try {
      await forgotPassword(email)
      ElMessage.success('Reset email sent if account exists')
      return true
    } finally {
      loading.value = false
    }
  }

  async function resetPwd(token, newPassword) {
    loading.value = true
    try {
      await resetPassword(token, newPassword)
      ElMessage.success('Password reset successfully')
      return true
    } finally {
      loading.value = false
    }
  }

  function logout() {
    localStorage.removeItem('token')
    user.value = null
  }

  return { user, loading, isAuthenticated, userEmail, init, login, register, verify, forgotPwd, resetPwd, logout }
})
