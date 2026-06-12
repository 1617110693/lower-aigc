<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCopyToClipboard } from '@/composables/useCopyToClipboard'

const props = defineProps({
  text: { type: String, required: true },
})
const { t } = useI18n()
const { copy } = useCopyToClipboard()
const copied = ref(false)

async function handleCopy() {
  const ok = await copy(props.text)
  if (ok) {
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  }
}
</script>

<template>
  <el-button
    size="small"
    :type="copied ? 'success' : 'default'"
    :icon="copied ? 'Check' : 'CopyDocument'"
    @click="handleCopy"
  >
    {{ copied ? t('reduction.copied') : t('reduction.copyParagraph') }}
  </el-button>
</template>
