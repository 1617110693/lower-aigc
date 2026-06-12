<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CopyButton from '@/components/common/CopyButton.vue'

const props = defineProps({
  paragraph: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['retry'])
const { t } = useI18n()

const hasReduced = computed(() => props.paragraph.is_reduced && props.paragraph.reduced_text)
const displayOriginal = computed(() => props.paragraph.original_text || '')
const displayReduced = computed(() => props.paragraph.reduced_text || '')

const isError = computed(() => {
  return displayReduced.value.startsWith('[Error:')
})
</script>

<template>
  <div class="paragraph-card" :class="{ reduced: hasReduced, error: isError }">
    <div class="card-header">
      <span class="card-badge">{{ t('reduction.original') }}</span>
      <span class="card-badge reduced-badge" v-if="hasReduced">{{ t('reduction.reduced') }}</span>
    </div>

    <div class="card-body">
      <div class="text-panel original-panel">
        <div class="text-content">{{ displayOriginal }}</div>
      </div>

      <div class="text-panel reduced-panel" v-if="hasReduced">
        <div class="text-content" :class="{ 'error-text': isError }">
          {{ displayReduced }}
        </div>
        <div class="panel-actions" v-if="!isError">
          <CopyButton :text="displayReduced" />
        </div>
      </div>

      <div class="text-panel reduced-panel" v-else>
        <div class="text-content empty-text">{{ t('reduction.noReduction') }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.paragraph-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.paragraph-card.reduced {
  border-color: #d5d0f5;
}

.paragraph-card.error {
  border-color: #fbc4c4;
}

.card-header {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

.card-badge {
  font-size: 12px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-badge.reduced-badge {
  color: #6c5ce7;
}

.card-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px;
}

@media (max-width: 768px) {
  .card-body {
    grid-template-columns: 1fr;
  }
}

.text-panel {
  min-height: 80px;
}

.text-content {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}

.text-content.empty-text {
  color: #c0c4cc;
  font-style: italic;
}

.text-content.error-text {
  color: #f56c6c;
}

.panel-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>
