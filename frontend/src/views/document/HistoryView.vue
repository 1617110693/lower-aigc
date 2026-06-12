<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { useDocumentStore } from '@/stores/document'

const { t } = useI18n()
const router = useRouter()
const docStore = useDocumentStore()
const loading = ref(false)

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
  <div class="history-page" v-loading="loading">
    <div class="history-header">
      <h1>{{ t('nav.history') }}</h1>
      <el-button type="primary" @click="router.push({ name: 'upload' })">
        <el-icon><Plus /></el-icon>{{ t('nav.upload') }}
      </el-button>
    </div>

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

    <el-empty v-else :description="t('document.noDocument')">
      <el-button type="primary" @click="router.push({ name: 'upload' })">
        {{ t('nav.upload') }}
      </el-button>
    </el-empty>

    <div v-if="docStore.pagination.total > docStore.pagination.size" class="pagination-wrap">
      <el-pagination
        v-model:current-page="docStore.pagination.page"
        :page-size="docStore.pagination.size"
        :total="docStore.pagination.total"
        layout="prev, pager, next"
        @current-change="(p) => docStore.fetchDocuments(p)"
      />
    </div>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 1200px;
  margin: 0 auto;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.history-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
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
