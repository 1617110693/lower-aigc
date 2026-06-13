import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  uploadDocument as apiUpload,
  listDocuments,
  getDocument,
  deleteDocument,
  startReduction,
  getReductionStatus,
  exportDocument,
  getPrompts,
} from '@/api/document'
import { ElMessage } from 'element-plus'

export const useDocumentStore = defineStore('document', () => {
  const currentDocument = ref(null)
  const documents = ref([])
  const pagination = ref({ total: 0, page: 1, size: 20 })
  const reductionStatus = ref(null)
  const isReducing = ref(false)
  const prompts = ref([])
  let pollTimer = null

  async function upload(file) {
    const res = await apiUpload(file)
    currentDocument.value = {
      document_id: res.data.document_id,
      paragraphs: res.data.paragraphs,
    }
    ElMessage.success('Document parsed successfully')
    return res.data
  }

  async function fetchDocuments(page = 1) {
    const res = await listDocuments(page, pagination.value.size)
    documents.value = res.data.items
    pagination.value = {
      total: res.data.total,
      page: res.data.page,
      size: res.data.size,
    }
  }

  async function fetchDocument(id) {
    const res = await getDocument(id)
    currentDocument.value = res.data
    return res.data
  }

  async function removeDocument(id) {
    await deleteDocument(id)
    ElMessage.success('Document deleted')
    await fetchDocuments()
  }

  async function fetchPrompts() {
    const res = await getPrompts()
    prompts.value = res.data
  }

  async function reduce(documentId, mode, promptId, paragraphIds = null, model = 'deepseek-v4-flash', preserveWordCount = false) {
    await startReduction(documentId, mode, promptId, paragraphIds, model, preserveWordCount)
    isReducing.value = true
    startPolling(documentId)
  }

  function startPolling(documentId) {
    stopPolling()
    pollTimer = setInterval(async () => {
      try {
        const res = await getReductionStatus(documentId)
        reductionStatus.value = res.data

        if (res.data.status === 'completed' || res.data.status === 'failed') {
          stopPolling()
          isReducing.value = false
          if (res.data.status === 'completed') {
            ElMessage.success('Reduction completed')
            await fetchDocument(documentId)
          } else {
            ElMessage.error('Reduction failed')
          }
        }
      } catch {
        stopPolling()
        isReducing.value = false
      }
    }, 2000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function exportDoc(documentId, filename) {
    const res = await exportDocument(documentId)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename || 'reduced.docx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Exported successfully')
  }

  return {
    currentDocument, documents, pagination, reductionStatus, isReducing, prompts,
    upload, fetchDocuments, fetchDocument, removeDocument, reduce, exportDoc,
    fetchPrompts, stopPolling, startPolling,
  }
})
