<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDocumentStore } from '@/stores/document'

const { t } = useI18n()
const router = useRouter()
const docStore = useDocumentStore()
const loading = ref(false)
const uploading = ref(false)
const fileList = ref([])

const statusMap = {
  uploaded: 'document.statusUploaded',
  parsed: 'document.statusParsed',
  reducing: 'document.statusReducing',
  completed: 'document.statusCompleted',
  failed: 'document.statusFailed',
}

const statusColors = {
  uploaded: 'info',
  parsed: 'warning',
  reducing: '',
  completed: 'success',
  failed: 'danger',
}

onMounted(async () => {
  loading.value = true
  try {
    await docStore.fetchDocuments()
  } finally {
    loading.value = false
  }
})

// ── 上传 ──────────────────────────────────────────────────────────────────────

async function handleUpload(options) {
  uploading.value = true
  try {
    const result = await docStore.upload(options.file)
    fileList.value = []
    await docStore.fetchDocuments()
    ElMessage.success(t('document.parseSuccess'))
    router.push({ name: 'reduce', params: { id: result.document_id } })
  } catch {
    // Error handled by interceptor
  } finally {
    uploading.value = false
  }
}

function beforeUpload(file) {
  const isDocx = file.name.toLowerCase().endsWith('.docx')
  if (!isDocx) {
    ElMessage.error(t('document.uploadTip'))
    return false
  }
  const isUnderLimit = file.size / 1024 / 1024 < 16
  if (!isUnderLimit) {
    ElMessage.error(t('document.uploadTip'))
    return false
  }
  return true
}

// ── 文档操作 ──────────────────────────────────────────────────────────────────

function viewDocument(doc) {
  router.push({ name: 'reduce', params: { id: doc.id } })
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(t('document.deleteConfirm'), t('common.confirm'), {
      type: 'warning',
    })
    await docStore.removeDocument(doc.id)
  } catch {
    // cancelled
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString()
}
</script>

<template>
  <div class="documents-page" v-loading="loading">
    <div class="documents-header">
      <h1>{{ t('nav.myDocuments') }}</h1>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section">
      <el-upload
        v-model:file-list="fileList"
        class="upload-dragger"
        drag
        :auto-upload="true"
        :show-file-list="false"
        :http-request="handleUpload"
        :before-upload="beforeUpload"
        accept=".docx"
      >
        <el-icon class="upload-icon" :size="40" color="#6c5ce7">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          <p class="upload-hint">{{ t('document.uploadHint') }}</p>
          <p class="upload-tip">{{ t('document.uploadTip') }}</p>
        </div>
      </el-upload>
      <div v-if="uploading" class="upload-progress">
        <el-progress :percentage="100" :indeterminate="true" :duration="2" />
        <p>{{ t('document.uploading') }}</p>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="documents-section">
      <h2 class="section-title">{{ t('nav.history') }}</h2>
      <el-table v-if="docStore.documents.length > 0" :data="docStore.documents" stripe style="width: 100%">
      <el-table-column prop="title" :label="t('document.title')" min-width="200">
        <template #default="{ row }">
          <span class="doc-title" @click="viewDocument(row)">{{ row.title || row.original_filename }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="original_filename" :label="t('document.filename')" min-width="180" />
      <el-table-column prop="status" :label="t('document.status')" width="120">
        <template #default="{ row }">
          <el-tag :type="statusColors[row.status] || 'info'" size="small">
            {{ t(statusMap[row.status] || row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('document.createdAt')" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="t('document.actions')" width="180">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="viewDocument(row)">
            {{ t('document.view') }}
          </el-button>
          <el-button size="small" type="danger" link @click="handleDelete(row)">
            {{ t('document.delete') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-else :description="t('document.noDocument')" />

    <div v-if="docStore.pagination.total > docStore.pagination.size" class="pagination-wrap">
      <el-pagination
        v-model:current-page="docStore.pagination.page"
        :page-size="docStore.pagination.size"
        :total="docStore.pagination.total"
        layout="prev, pager, next"
        @current-change="(p) => docStore.fetchDocuments(p)"
      />
    </div>
    </div><!-- .documents-section -->
  </div>
</template>

<style scoped>
.documents-page {
  max-width: 1200px;
  margin: 0 auto;
}

.documents-header {
  margin-bottom: 24px;
}

.documents-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

/* ── 上传区域 ─────────────────────────────────────────────── */

.upload-section {
  margin-bottom: 32px;
}

.upload-dragger :deep(.el-upload-dragger) {
  background: #fff;
  border: 2px dashed #d9d9d9;
  border-radius: 16px;
  padding: 36px 24px;
  transition: border-color 0.3s, background 0.3s;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: #6c5ce7;
  background: #faf9ff;
}

.upload-icon {
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 16px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-tip {
  font-size: 13px;
  color: #c0c4cc;
  margin: 0;
}

.upload-progress {
  text-align: center;
  padding: 16px 0 0;
}

.upload-progress p {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

/* ── 文档列表 ─────────────────────────────────────────────── */

.documents-section {
  /* container for the table area */
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #909399;
  margin: 0 0 16px;
}

.doc-title {
  color: #6c5ce7;
  cursor: pointer;
  font-weight: 500;
}

.doc-title:hover {
  text-decoration: underline;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
