import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { logRequest, logResponse, logError } from '@/utils/logger'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  logRequest(config)
  return config
})

api.interceptors.response.use(
  (response) => {
    logResponse(response)
    return response
  },
  (error) => {
    logError(error)

    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      const auth = useAuthStore()
      auth.user = null
    }

    // 格式化 Pydantic 验证错误 (422) 的 detail 字段
    let msg = error.response?.data?.detail
    if (Array.isArray(msg)) {
      msg = msg
        .map((e) => {
          const loc = e.loc?.join('.') || ''
          return `${e.msg}${loc ? ` (${loc})` : ''}`
        })
        .join('; ')
    }
    if (!msg) {
      msg = error.message || 'Network error'
    }
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default api
