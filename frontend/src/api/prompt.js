import api from './index'

// ── 自定义改写策略 CRUD ───────────────────────────────────────────────────────

export function listCustomPrompts() {
  return api.get('/system/prompts')
}

export function createCustomPrompt(data) {
  return api.post('/system/prompts', data)
}

export function updateCustomPrompt(id, data) {
  return api.put(`/system/prompts/${id}`, data)
}

export function deleteCustomPrompt(id) {
  return api.delete(`/system/prompts/${id}`)
}
