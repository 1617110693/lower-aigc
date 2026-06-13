import api from './index'

export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function listDocuments(page = 1, size = 20) {
  return api.get('/documents/', { params: { page, size } })
}

export function getDocument(id) {
  return api.get(`/documents/${id}`)
}

export function deleteDocument(id) {
  return api.delete(`/documents/${id}`)
}

export function startReduction(id, mode, promptId, paragraphIds = null) {
  return api.post(`/documents/${id}/reduce`, {
    mode,
    prompt_id: promptId,
    paragraph_ids: paragraphIds,
  })
}

export function getReductionStatus(id) {
  return api.get(`/documents/${id}/status`)
}

export function exportDocument(id) {
  return api.get(`/documents/${id}/export`, {
    responseType: 'blob',
  })
}

export function getPrompts() {
  return api.get('/documents/prompts')
}

export function reduceText(text, promptId) {
  return api.post('/system/reduce-text', {
    text,
    prompt_id: promptId,
  })
}
