<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()
</script>

<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <h1>404</h1>
      <p>{{ t('common.notFound') }}</p>
      <el-button type="primary" @click="router.push({ name: 'home' })">
        {{ t('common.backHome') }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
  text-align: center;
}

.not-found-content h1 {
  font-size: 72px;
  font-weight: 800;
  color: #6c5ce7;
  margin: 0 0 8px;
}

.not-found-content p {
  font-size: 16px;
  color: #909399;
  margin-bottom: 24px;
}
</style>
