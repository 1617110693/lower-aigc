<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useDocumentStore } from '@/stores/document'

const { t } = useI18n()
const router = useRouter()
const docStore = useDocumentStore()
const uploading = ref(false)
const fileList = ref([])

async function handleUpload(options) {
  uploading.value = true
  try {
    const result = await docStore.upload(options.file)
    router.push({ name: 'reduce', params: { id: result.document_id } })
  } catch {
    // Error handled by interceptor
  } finally {
    uploading.value = false
    fileList.value = []
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
</script>

<template>
  <div class="upload-page">
    <div class="upload-header">
      <h1>{{ t('document.uploadTitle') }}</h1>
      <p>{{ t('document.uploadTip') }}</p>
    </div>

    <div class="upload-area">
      <el-upload
        v-model:file-list="fileList"
        class="upload-dragger"
        drag
        :auto-upload="false"
        :show-file-list="false"
        :http-request="handleUpload"
        :before-upload="beforeUpload"
        accept=".docx"
      >
        <el-icon class="upload-icon" :size="64" color="#6c5ce7">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          <p class="upload-hint">{{ t('document.uploadHint') }}</p>
          <p class="upload-tip">{{ t('document.uploadTip') }}</p>
        </div>
      </el-upload>
    </div>

    <div v-if="uploading" class="upload-progress">
      <el-progress :percentage="100" :indeterminate="true" :duration="2" />
      <p>{{ t('document.uploading') }}</p>
    </div>
  </div>
</template>

<style scoped>
.upload-page {
  max-width: 700px;
  margin: 0 auto;
  padding-top: 40px;
}

.upload-header {
  text-align: center;
  margin-bottom: 36px;
}

.upload-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 8px;
}

.upload-header p {
  color: #909399;
  font-size: 14px;
}

.upload-area {
  margin-bottom: 24px;
}

.upload-dragger :deep(.el-upload-dragger) {
  background: #fff;
  border: 2px dashed #d9d9d9;
  border-radius: 16px;
  padding: 60px 40px;
  transition: border-color 0.3s, background 0.3s;
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: #6c5ce7;
  background: #faf9ff;
}

.upload-icon {
  margin-bottom: 16px;
}

.upload-hint {
  font-size: 18px;
  color: #303133;
  font-weight: 500;
  margin-bottom: 8px;
}

.upload-tip {
  font-size: 13px;
  color: #c0c4cc;
}

.upload-progress {
  text-align: center;
  padding: 20px 0;
}

.upload-progress p {
  margin-top: 12px;
  color: #909399;
}
</style>
