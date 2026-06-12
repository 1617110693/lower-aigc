<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  newPassword: '',
})

const showResetForm = ref(!!route.query.token)
const resetToken = ref(route.query.token || '')

async function handleForgot() {
  if (!form.email) return
  await authStore.forgotPwd(form.email)
}

async function handleReset() {
  if (!form.newPassword || form.newPassword.length < 6) return
  const ok = await authStore.resetPwd(resetToken.value, form.newPassword)
  if (ok) {
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <el-icon :size="40" color="#6c5ce7"><Lock /></el-icon>
        <h2>{{ t('auth.resetTitle') }}</h2>
      </div>

      <template v-if="showResetForm">
        <el-form @submit.prevent="handleReset">
          <el-form-item :label="t('auth.newPassword')">
            <el-input
              v-model="form.newPassword"
              type="password"
              :placeholder="t('auth.newPassword')"
              prefix-icon="Lock"
              size="large"
              show-password
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            block
            @click="handleReset"
          >
            {{ t('auth.resetBtn') }}
          </el-button>
        </el-form>
      </template>

      <template v-else>
        <el-form @submit.prevent="handleForgot">
          <el-form-item :label="t('auth.email')">
            <el-input
              v-model="form.email"
              :placeholder="t('auth.email')"
              prefix-icon="Message"
              size="large"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            block
            @click="handleForgot"
          >
            {{ t('auth.sendResetEmail') }}
          </el-button>
        </el-form>
      </template>

      <div class="auth-switch">
        <router-link to="/login">{{ t('auth.goLogin') }}</router-link>
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
  padding: 40px 20px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-header h2 {
  margin-top: 12px;
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.auth-switch {
  text-align: center;
  margin-top: 24px;
}

.auth-switch a {
  color: #6c5ce7;
  text-decoration: none;
  font-size: 14px;
}
</style>
