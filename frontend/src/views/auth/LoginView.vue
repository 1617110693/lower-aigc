<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  password: '',
})

const rules = {
  email: [
    { required: true, message: 'Email is required', trigger: 'blur' },
    { type: 'email', message: () => t('auth.invalidEmail'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: 'Password is required', trigger: 'blur' },
  ],
}

const formRef = ref(null)
const authLoading = computed(() => authStore.loading)

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  const ok = await authStore.login(form.email, form.password)
  if (ok) {
    const redirect = route.query.redirect || '/documents/upload'
    router.push(redirect)
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <el-icon :size="40" color="#6c5ce7"><Document /></el-icon>
        <h2>{{ t('auth.loginTitle') }}</h2>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item :label="t('auth.email')" prop="email">
          <el-input
            v-model="form.email"
            :placeholder="t('auth.email')"
            prefix-icon="Message"
            size="large"
          />
        </el-form-item>

        <el-form-item :label="t('auth.password')" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="t('auth.password')"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="authLoading"
          class="submit-btn"
          block
        >
          {{ t('auth.loginBtn') }}
        </el-button>

        <div class="auth-links">
          <router-link to="/reset-password">{{ t('auth.forgotPassword') }}</router-link>
        </div>

        <div class="auth-switch">
          {{ t('auth.noAccount') }}
          <router-link to="/register">{{ t('auth.goRegister') }}</router-link>
        </div>
      </el-form>
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

.submit-btn {
  margin-top: 8px;
  height: 44px;
  font-size: 16px;
}

.auth-links {
  text-align: right;
  margin-top: 12px;
}

.auth-links a {
  color: #6c5ce7;
  font-size: 14px;
  text-decoration: none;
}

.auth-switch {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #909399;
}

.auth-switch a {
  color: #6c5ce7;
  text-decoration: none;
  font-weight: 500;
}
</style>
