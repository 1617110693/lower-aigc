<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

const props = defineProps({
  prompts: { type: Array, default: () => [] },
  isReducing: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['reduce'])

const { t } = useI18n()
const mode = ref('full')
const selectedPrompt = ref('')
const selectedModel = ref('deepseek-v4-flash')
const preserveWordCount = ref(false)

const modelOptions = [
  { id: 'deepseek-v4-flash', label: 'deepseek-v4-flash' },
  { id: 'deepseek-v4-pro', label: 'deepseek-v4-pro' },
]

const canReduce = computed(() => {
  return !props.isReducing && selectedPrompt.value
})

const selectedStrategy = computed(() =>
  props.prompts.find((p) => p.id === selectedPrompt.value)
)

function handleReduce() {
  if (!selectedPrompt.value) {
    ElMessage.warning(t('reduction.selectPrompt'))
    return
  }
  emit('reduce', mode.value, selectedPrompt.value, null, selectedModel.value, preserveWordCount.value)
}
</script>

<template>
  <div class="controls-card">
    <div class="controls-row">
      <div class="control-group">
        <label>{{ t('reduction.modeLabel') }}</label>
        <el-radio-group v-model="mode" :disabled="isReducing">
          <el-radio-button value="full">{{ t('reduction.modeFullText') }}</el-radio-button>
          <el-radio-button value="paragraph">{{ t('reduction.modeParagraph') }}</el-radio-button>
        </el-radio-group>
      </div>

      <div class="control-group">
        <label>{{ t('reduction.modelLabel') }}</label>
        <el-select
          v-model="selectedModel"
          :disabled="isReducing"
          style="width: 180px"
        >
          <el-option
            v-for="m in modelOptions"
            :key="m.id"
            :label="m.label"
            :value="m.id"
          />
        </el-select>
      </div>

      <div class="control-group">
        <label>{{ t('reduction.promptLabel') }}</label>
        <el-select
          v-model="selectedPrompt"
          :placeholder="t('reduction.selectPrompt')"
          :disabled="isReducing"
          style="width: 240px"
        >
          <el-option
            v-for="p in prompts"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          >
            <span>{{ p.name }}</span>
            <el-tag v-if="!p.system_default" size="small" type="warning" style="margin-left: 6px; float: right;">{{ t('prompts.custom') }}</el-tag>
          </el-option>
        </el-select>
      </div>

      <div class="control-group">
        <el-tooltip :content="t('reduction.preserveWordCount')" placement="top">
          <el-checkbox v-model="preserveWordCount" :disabled="isReducing" border size="small">
            {{ t('reduction.preserveWordCount') }}
          </el-checkbox>
        </el-tooltip>
      </div>

      <div class="control-actions">
        <el-button
          type="primary"
          size="large"
          :disabled="!canReduce"
          :loading="loading"
          @click="handleReduce"
        >
          <el-icon v-if="!loading"><MagicStick /></el-icon>
          {{ t('reduction.startBtn') }}
        </el-button>
      </div>
    </div>

    <!-- 选中策略的描述提示 -->
    <div v-if="selectedStrategy" class="strategy-hint">
      <el-icon><InfoFilled /></el-icon>
      {{ selectedStrategy.description }}
    </div>
  </div>
</template>

<style scoped>
.controls-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  border: 1px solid #ebeef5;
  margin-bottom: 8px;
}

.controls-row {
  display: flex;
  align-items: flex-end;
  gap: 24px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-group label {
  font-size: 13px;
  font-weight: 600;
  color: #909399;
}

.control-actions {
  margin-left: auto;
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
  margin-top: 16px;
}
</style>
