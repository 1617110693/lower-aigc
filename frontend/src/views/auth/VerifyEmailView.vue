<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const status = ref('loading')

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    status.value = 'error'
    return
  }
  const ok = await authStore.verify(token)
  status.value = ok ? 'success' : 'error'
  if (ok) {
    setTimeout(() => router.push({ name: 'login' }), 3000)
  }
})
</script>

<template>
  <div class="auth-page">
    <div class="verify-card">
      <div v-if="status === 'loading'" class="verify-content">
        <el-icon class="is-loading" :size="48" color="#6c5ce7"><Loading /></el-icon>
        <h3>{{ t('auth.verifying') }}</h3>
      </div>
      <div v-else-if="status === 'success'" class="verify-content success">
        <el-icon :size="48" color="#67c23a"><CircleCheckFilled /></el-icon>
        <h3>{{ t('auth.verifySuccess') }}</h3>
      </div>
      <div v-else class="verify-content error">
        <el-icon :size="48" color="#f56c6c"><CircleCloseFilled /></el-icon>
        <h3>{{ t('common.error') }}</h3>
        <el-button type="primary" @click="router.push({ name: 'login' })">
          {{ t('nav.login') }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 60px - 52px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.verify-card {
  background: #fff;
  border-radius: 16px;
  padding: 60px 40px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.verify-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.verify-content h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}
</style>
