import api from './index'

export function login(email, password) {
  return api.post('/auth/login', { email, password })
}

export function register(email, password) {
  return api.post('/auth/register', { email, password })
}

export function verifyEmail(token) {
  return api.post('/auth/verify-email', { token })
}

export function getMe() {
  return api.get('/auth/me')
}

export function forgotPassword(email) {
  return api.post('/auth/forgot-password', { email })
}

export function resetPassword(token, newPassword) {
  return api.post('/auth/reset-password', { token, new_password: newPassword })
}
