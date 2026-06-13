<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { reduceText } from '@/api/document'
import CopyButton from '@/components/common/CopyButton.vue'

const { t } = useI18n()

const inputText = ref('')
const reducedText = ref('')
const loading = ref(false)
const selectedPrompt = ref('academic-paraphrase')
const hasResult = computed(() => reducedText.value.length > 0)

// 降低AIGC策略列表
const strategyOptions = [
  { id: 'academic-paraphrase', name: '学术改写', desc: '变换句式结构，使用学科词汇，保持学术严谨性' },
  { id: 'style-diversification', name: '风格多样化', desc: '长短句交替，添加过渡语，融入领域术语' },
  { id: 'natural-human-voice', name: '自然人声', desc: '增加适度不完美，模拟真人写作风格' },
]

const selectedStrategy = computed(() =>
  strategyOptions.find((s) => s.id === selectedPrompt.value)
)

async function handleReduce() {
  const text = inputText.value.trim()
  if (!text) {
    ElMessage.warning(t('quickReduce.emptyWarning'))
    return
  }
  if (text.length < 10) {
    ElMessage.warning(t('quickReduce.tooShort'))
    return
  }

  loading.value = true
  try {
    const res = await reduceText(text, selectedPrompt.value)
    reducedText.value = res.data.reduced_text
    ElMessage.success(t('quickReduce.success'))
  } catch (err) {
    const msg = err?.response?.data?.detail || t('quickReduce.error')
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function handleClear() {
  inputText.value = ''
  reducedText.value = ''
}
</script>

<template>
  <div class="quick-reduce-page">
    <div class="page-header">
      <h1>{{ t('quickReduce.title') }}</h1>
      <p>{{ t('quickReduce.desc') }}</p>
    </div>

    <div class="reduce-workspace">
      <!-- 策略选择 -->
      <div class="toolbar">
        <div class="strategy-selector">
          <span class="toolbar-label">{{ t('quickReduce.strategy') }}</span>
          <el-select v-model="selectedPrompt" :disabled="loading" class="strategy-select">
            <el-option
              v-for="s in strategyOptions"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            >
              <span>{{ s.name }}</span>
              <span class="strategy-desc">{{ s.desc }}</span>
            </el-option>
          </el-select>
        </div>
        <div class="toolbar-actions">
          <el-button
            type="primary"
            :loading="loading"
            :disabled="!inputText.trim()"
            @click="handleReduce"
          >
            <el-icon v-if="!loading"><MagicStick /></el-icon>
            {{ loading ? t('quickReduce.processing') : t('quickReduce.startBtn') }}
          </el-button>
          <el-button @click="handleClear" :disabled="!inputText && !reducedText">
            {{ t('quickReduce.clear') }}
          </el-button>
        </div>
      </div>

      <!-- 策略描述 -->
      <div v-if="selectedStrategy" class="strategy-hint">
        <el-icon><InfoFilled /></el-icon>
        {{ selectedStrategy.desc }}
      </div>

      <!-- 输入区域 -->
      <div class="text-panels">
        <div class="text-panel input-panel">
          <div class="panel-header">
            <span class="panel-label">{{ t('quickReduce.inputLabel') }}</span>
            <span class="char-count">{{ inputText.length }} {{ t('quickReduce.chars') }}</span>
          </div>
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="14"
            :placeholder="t('quickReduce.placeholder')"
            :disabled="loading"
            resize="vertical"
            class="text-input"
          />
        </div>

        <div class="text-panel output-panel">
          <div class="panel-header">
            <span class="panel-label">{{ t('quickReduce.outputLabel') }}</span>
            <CopyButton v-if="hasResult" :text="reducedText" />
          </div>
          <div class="output-content" :class="{ empty: !hasResult, loading: loading }">
            <template v-if="loading">
              <el-icon class="loading-icon is-loading"><Loading /></el-icon>
              <span>{{ t('quickReduce.processing') }}</span>
            </template>
            <template v-else-if="hasResult">
              {{ reducedText }}
            </template>
            <template v-else>
              <span class="empty-hint">{{ t('quickReduce.resultHint') }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-reduce-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 8px;
}

.page-header p {
  color: #909399;
  font-size: 14px;
}

.reduce-workspace {
  background: #fff;
  border-radius: 16px;
  border: 1px solid #ebeef5;
  padding: 24px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.strategy-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-label {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  white-space: nowrap;
}

.strategy-select {
  width: 220px;
}

.strategy-desc {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.strategy-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #909399;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.text-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 900px) {
  .text-panels {
    grid-template-columns: 1fr;
  }
}

.text-panel {
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.char-count {
  font-size: 12px;
  color: #c0c4cc;
}

.text-input :deep(.el-textarea__inner) {
  font-size: 14px;
  line-height: 1.8;
  border-radius: 10px;
  border-color: #e4e7ed;
  transition: border-color 0.3s;
  min-height: 280px;
}

.text-input :deep(.el-textarea__inner):focus {
  border-color: #6c5ce7;
}

.output-content {
  min-height: 280px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  padding: 14px;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.output-content:not(.empty) {
  display: block;
  align-items: initial;
  justify-content: initial;
  background: #f9fafb;
}

.output-content.loading {
  flex-direction: column;
  gap: 10px;
  color: #909399;
}

.loading-icon {
  font-size: 24px;
  color: #6c5ce7;
}

.empty-hint {
  color: #c0c4cc;
  font-size: 14px;
}
</style>
