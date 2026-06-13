<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  reduceText,
  getPrompts,
  fetchQuickReduceHistory,
  saveQuickReduceHistory,
  deleteQuickReduceHistoryEntry,
  clearQuickReduceHistory as apiClearHistory,
} from '@/api/document'
import { logger } from '@/utils/logger'
import CopyButton from '@/components/common/CopyButton.vue'

const { t } = useI18n()
const router = useRouter()

const inputText = ref('')
const reducedText = ref('')
const loading = ref(false)
const selectedPrompt = ref('academic-paraphrase')
const selectedModel = ref('deepseek-v4-flash')
const preserveWordCount = ref(false)
const hasResult = computed(() => (reducedText.value || '').length > 0)

// 模型选项
const modelOptions = [
  { id: 'deepseek-v4-flash', label: 'deepseek-v4-flash' },
  { id: 'deepseek-v4-pro', label: 'deepseek-v4-pro' },
]

// 降低AIGC策略列表（从 API 动态加载，失败时 fallback 内置策略）
const BUILTIN_FALLBACK = [
  { id: 'academic-paraphrase', name: '学术改写', desc: '变换句式结构，使用学科词汇，保持学术严谨性', systemDefault: true },
  { id: 'style-diversification', name: '风格多样化', desc: '长短句交替，添加过渡语，融入领域术语', systemDefault: true },
  { id: 'natural-human-voice', name: '自然人声', desc: '增加适度不完美，模拟真人写作风格', systemDefault: true },
]

const strategyOptions = ref([])

async function loadStrategies() {
  try {
    const res = await getPrompts()
    strategyOptions.value = (res.data || []).map((p) => ({
      id: p.id,
      name: p.name,
      desc: p.description,
      systemDefault: p.system_default,
    }))
    // 如果当前选中策略不存在（可能已被删除），回退到默认
    if (!strategyOptions.value.find((s) => s.id === selectedPrompt.value)) {
      selectedPrompt.value = 'academic-paraphrase'
    }
  } catch (err) {
    logger.warn('QuickReduce', 'Failed to load strategies, using fallback', err)
    strategyOptions.value = BUILTIN_FALLBACK
  }
}

const selectedStrategy = computed(() =>
  strategyOptions.value.find((s) => s.id === selectedPrompt.value)
)

// ── 历史记录 (服务端存储) ────────────────────────────────────────────────────

const MAX_HISTORY = 50

const history = ref([])

async function loadHistory() {
  try {
    const res = await fetchQuickReduceHistory()
    history.value = (res.data?.items || []).map((item) => ({
      id: item.id,
      originalText: item.original_text,
      reducedText: item.reduced_text,
      promptId: item.prompt_id,
      model: item.model,
      preserveWordCount: item.preserve_word_count,
      timestamp: new Date(item.created_at).getTime(),
    }))
  } catch {
    history.value = []
  }
}

async function saveHistoryEntry(originalText, reducedText) {
  const entry = {
    originalText,
    reducedText,
    promptId: selectedPrompt.value,
    model: selectedModel.value,
    preserveWordCount: preserveWordCount.value,
  }
  try {
    const res = await saveQuickReduceHistory(entry)
    history.value.unshift({
      id: res.data.id,
      ...entry,
      timestamp: Date.now(),
    })
    if (history.value.length > MAX_HISTORY) {
      history.value = history.value.slice(0, MAX_HISTORY)
    }
  } catch {
    // 保存失败不影响使用
  }
}

async function clearHistory() {
  try {
    await ElMessageBox.confirm(t('quickReduce.clearHistory') + '?', '', {
      confirmButtonText: t('common.ok'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    await apiClearHistory()
    history.value = []
    ElMessage.success(t('quickReduce.historyCleared'))
  } catch {
    // cancelled or API error
  }
}

function loadHistoryEntry(entry) {
  inputText.value = entry.originalText
  reducedText.value = entry.reducedText
  selectedPrompt.value = entry.promptId
  selectedModel.value = entry.model
  preserveWordCount.value = entry.preserveWordCount
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function deleteHistoryEntry(entryId) {
  history.value = history.value.filter((e) => e.id !== entryId)
  try { await deleteQuickReduceHistoryEntry(entryId) } catch { /* 忽略 */ }
}

function formatTime(ts) {
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function previewText(text, maxLen = 80) {
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
}

const strategyName = (promptId) =>
  strategyOptions.value.find((s) => s.id === promptId)?.name || promptId

// ── 降低AIGC ────────────────────────────────────────────────────────────────

async function handleReduce() {
  // 防止重复提交
  if (loading.value) return

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
    const res = await reduceText(text, selectedPrompt.value, selectedModel.value, preserveWordCount.value)
    // 调试日志：打印完整响应结构
    console.log('QuickReduce API response:', {
      status: res.status,
      dataKeys: Object.keys(res.data || {}),
      original_text: (res.data?.original_text || '').substring(0, 50),
      reduced_text: (res.data?.reduced_text || '').substring(0, 50),
      reduced_text_type: typeof res.data?.reduced_text,
      reduced_text_length: res.data?.reduced_text?.length,
    })
    const result = res.data?.reduced_text
    if (!result) {
      console.error('QuickReduce: empty response from API', res.data)
      ElMessage.error(t('quickReduce.error'))
      return
    }
    reducedText.value = result
    saveHistoryEntry(text, result)
    ElMessage.success(t('quickReduce.success'))
  } catch (err) {
    console.error('QuickReduce: API error', err)
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

// 初始化
onMounted(() => {
  loadHistory()
  loadStrategies()
})
</script>

<template>
  <div class="quick-reduce-page">
    <div class="page-header">
      <h1>{{ t('quickReduce.title') }}</h1>
      <p>{{ t('quickReduce.desc') }}</p>
    </div>

    <div class="reduce-workspace">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-selectors">
          <div class="strategy-selector">
            <span class="toolbar-label">{{ t('quickReduce.model') }}</span>
            <el-select v-model="selectedModel" :disabled="loading" class="model-select">
              <el-option
                v-for="m in modelOptions"
                :key="m.id"
                :label="m.label"
                :value="m.id"
              />
            </el-select>
          </div>
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
                <el-tag v-if="!s.systemDefault" size="small" type="warning" class="custom-tag">{{ t('prompts.custom') }}</el-tag>
                <span class="strategy-desc">{{ s.desc }}</span>
              </el-option>
            </el-select>
          </div>
          <el-checkbox v-model="preserveWordCount" :disabled="loading" border size="small">
            {{ t('quickReduce.preserveWordCount') }}
          </el-checkbox>
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

      <!-- 输入/输出区域 -->
      <div class="text-panels">
        <div class="text-panel input-panel">
          <div class="panel-header">
            <span class="panel-label">{{ t('quickReduce.inputLabel') }}</span>
            <span class="char-count">{{ inputText.length }} {{ t('quickReduce.chars') }}</span>
          </div>
          <el-input
            v-model="inputText"
            type="textarea"
            :placeholder="t('quickReduce.placeholder')"
            :disabled="loading"
            resize="none"
            class="text-input"
          />
        </div>

        <div class="text-panel output-panel">
          <div class="panel-header">
            <span class="panel-label">{{ t('quickReduce.outputLabel') }}</span>
            <div class="panel-header-right">
              <span v-if="hasResult" class="char-count">{{ reducedText.length }} {{ t('quickReduce.chars') }}</span>
              <CopyButton v-if="hasResult" :text="reducedText" />
            </div>
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

    <!-- 历史记录 -->
    <div v-if="history.length" class="history-section">
      <div class="history-header">
        <h2>{{ t('quickReduce.history') }}</h2>
        <el-button text type="danger" size="small" @click="clearHistory">
          {{ t('quickReduce.clearHistory') }}
        </el-button>
      </div>
      <div class="history-list">
        <div
          v-for="entry in history"
          :key="entry.id"
          class="history-item"
          @click="loadHistoryEntry(entry)"
        >
          <div class="history-meta">
            <span class="history-time">{{ formatTime(entry.timestamp) }}</span>
            <span class="history-strategy">{{ strategyName(entry.promptId) }}</span>
            <span class="history-model">{{ entry.model }}</span>
            <span v-if="entry.preserveWordCount" class="history-tag">{{ t('quickReduce.preserveWordCount') }}</span>
          </div>
          <div class="history-preview">{{ previewText(entry.originalText) }}</div>
          <el-button
            class="history-delete"
            text
            size="small"
            @click.stop="deleteHistoryEntry(entry.id)"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-reduce-page {
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 60px;
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

.toolbar-selectors {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
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

.model-select {
  width: 200px;
}

.strategy-select {
  width: 220px;
}

.custom-tag {
  margin-left: 6px;
  vertical-align: middle;
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
  min-height: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-shrink: 0;
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

.panel-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.text-input {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.text-input :deep(.el-textarea) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.text-input :deep(.el-textarea__inner) {
  flex: 1;
  font-size: 14px;
  line-height: 1.8;
  border-radius: 10px;
  border-color: #e4e7ed;
  transition: border-color 0.3s;
  resize: none;
  min-height: 280px;
}

.text-input :deep(.el-textarea__inner):focus {
  border-color: #6c5ce7;
}

.output-content {
  flex: 1;
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
  min-height: 280px;
  overflow-y: auto;
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

/* ── 历史记录 ─────────────────────────────────────────────── */

.history-section {
  margin-top: 32px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #ebeef5;
  padding: 24px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  position: relative;
}

.history-item:hover {
  background: #f5f7fa;
  border-color: #d3d7e0;
}

.history-delete {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.2s;
  color: #c0c4cc;
}

.history-item:hover .history-delete {
  opacity: 1;
}

.history-delete:hover {
  color: #f56c6c;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.history-time {
  font-size: 12px;
  color: #c0c4cc;
}

.history-strategy {
  font-size: 12px;
  color: #6c5ce7;
  background: #f0edff;
  padding: 2px 8px;
  border-radius: 4px;
}

.history-model {
  font-size: 12px;
  color: #909399;
}

.history-tag {
  font-size: 11px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 1px 6px;
  border-radius: 4px;
}

.history-preview {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
</style>
