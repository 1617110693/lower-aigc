<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDocumentStore } from '@/stores/document'
import { useCopyToClipboard } from '@/composables/useCopyToClipboard'
import ParagraphCard from '@/components/document/ParagraphCard.vue'
import ReductionControls from '@/components/document/ReductionControls.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const docStore = useDocumentStore()
const { copy } = useCopyToClipboard()

const documentId = computed(() => Number(route.params.id))
const loading = ref(true)
const exportLoading = ref(false)
const reduceLoading = ref(false)

const doc = computed(() => docStore.currentDocument)
const paragraphs = computed(() => doc.value?.paragraphs || [])
const isReducing = computed(() => docStore.isReducing)
const reductionProgress = computed(() => docStore.reductionStatus?.progress || 0)
const reductionStatus = computed(() => docStore.reductionStatus?.status)

onMounted(async () => {
  try {
    await docStore.fetchDocument(documentId.value)
    await docStore.fetchPrompts()
  } catch {
    ElMessage.error('Document not found')
    router.push({ name: 'upload' })
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  docStore.stopPolling()
})

async function handleReduce(mode, promptId, paragraphIds) {
  reduceLoading.value = true
  try {
    await docStore.reduce(documentId.value, mode, promptId, paragraphIds)
  } catch {
    // handled by interceptor
  } finally {
    reduceLoading.value = false
  }
}

async function handleExport() {
  exportLoading.value = true
  try {
    const filename = doc.value?.original_filename?.replace('.docx', '_reduced.docx') || 'reduced.docx'
    await docStore.exportDoc(documentId.value, filename)
  } finally {
    exportLoading.value = false
  }
}

async function copyAll() {
  const allText = paragraphs.value
    .map((p) => p.reduced_text || p.original_text)
    .join('\n\n')
  const ok = await copy(allText)
  if (ok) ElMessage.success(t('reduction.copied'))
}

async function handleRetryParagraph(paragraphId) {
  if (!docStore.prompts.length) return
  const promptId = docStore.prompts[0].id
  try {
    await docStore.reduce(documentId.value, 'paragraph', promptId, [paragraphId])
  } catch {
    // handled
  }
}
</script>

<template>
  <div class="reduction-page" v-loading="loading">
    <template v-if="doc">
      <!-- Header -->
      <div class="reduction-header">
        <div class="header-left">
          <el-button text @click="router.push({ name: 'history' })">
            <el-icon><ArrowLeft /></el-icon>{{ t('common.back') }}
          </el-button>
          <h1>{{ doc.title || doc.original_filename }}</h1>
        </div>
        <div class="header-actions">
          <el-button @click="copyAll" :disabled="paragraphs.length === 0">
            <el-icon><CopyDocument /></el-icon>{{ t('reduction.copyAll') }}
          </el-button>
          <el-button type="primary" @click="handleExport" :loading="exportLoading" :disabled="paragraphs.length === 0">
            <el-icon><Download /></el-icon>{{ t('reduction.exportBtn') }}
          </el-button>
        </div>
      </div>

      <!-- Reduction Controls -->
      <ReductionControls
        :prompts="docStore.prompts"
        :is-reducing="isReducing"
        :loading="reduceLoading"
        @reduce="handleReduce"
      />

      <!-- Progress bar -->
      <div v-if="isReducing" class="progress-bar">
        <el-progress :percentage="reductionProgress" :stroke-width="6" :color="'#6c5ce7'" />
        <p>{{ t('reduction.reducing') }} ({{ reductionProgress }}%)</p>
      </div>

      <div v-else-if="reductionStatus === 'completed'" class="status-banner success">
        <el-icon><CircleCheckFilled /></el-icon>{{ t('reduction.completed') }}
      </div>

      <div v-else-if="reductionStatus === 'failed'" class="status-banner error">
        <el-icon><CircleCloseFilled /></el-icon>{{ t('reduction.failed') }}
      </div>

      <!-- Paragraphs list -->
      <div class="paragraphs-container">
        <ParagraphCard
          v-for="para in paragraphs"
          :key="para.id"
          :paragraph="para"
          :disabled="false"
          @retry="handleRetryParagraph"
        />
        <el-empty v-if="paragraphs.length === 0" :description="t('document.noDocument')" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.reduction-page {
  max-width: 1200px;
  margin: 0 auto;
}

.reduction-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  font-size: 22px;
  font-weight: 700;
  color: #2c3e50;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.progress-bar {
  margin: 24px 0;
  text-align: center;
}

.progress-bar p {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 8px;
  margin: 16px 0;
  font-size: 15px;
  font-weight: 500;
}

.status-banner.success {
  background: #f0f9eb;
  color: #67c23a;
}

.status-banner.error {
  background: #fef0f0;
  color: #f56c6c;
}

.paragraphs-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 24px;
}
</style>
