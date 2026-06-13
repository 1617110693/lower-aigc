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

export function startReduction(id, mode, promptId, paragraphIds = null, model = 'deepseek-v4-flash', preserveWordCount = false) {
  return api.post(`/documents/${id}/reduce`, {
    mode,
    prompt_id: promptId,
    model,
    preserve_word_count: preserveWordCount,
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

export function reduceText(text, promptId, model = 'deepseek-v4-flash', preserveWordCount = false) {
  return api.post('/system/reduce-text', {
    text,
    prompt_id: promptId,
    model,
    preserve_word_count: preserveWordCount,
  })
}

// ── 快速降低AIGC历史记录（服务端，需登录）──────────────────────────────────────

export function fetchQuickReduceHistory(page = 1, size = 50) {
  return api.get('/system/quick-reduce-history', { params: { page, size } })
}

export function saveQuickReduceHistory(entry) {
  // 后端 Pydantic 模型使用 snake_case，前端使用 camelCase，需转换
  return api.post('/system/quick-reduce-history', {
    original_text: entry.originalText,
    reduced_text: entry.reducedText,
    prompt_id: entry.promptId,
    model: entry.model,
    preserve_word_count: entry.preserveWordCount,
  })
}

export function deleteQuickReduceHistoryEntry(entryId) {
  return api.delete(`/system/quick-reduce-history/${entryId}`)
}

export function clearQuickReduceHistory() {
  return api.delete('/system/quick-reduce-history')
}
