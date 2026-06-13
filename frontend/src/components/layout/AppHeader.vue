<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const currentLocaleLabel = computed(() => (appStore.locale === 'zh-CN' ? 'EN' : '中'))

function toggleLocale() {
  const next = appStore.locale === 'zh-CN' ? 'en' : 'zh-CN'
  appStore.setLocale(next)
  locale.value = next
}

function goHome() {
  router.push({ name: 'home' })
}

function logout() {
  authStore.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <el-header class="app-header">
    <div class="header-inner">
      <div class="header-left" @click="goHome">
        <el-icon :size="28" color="#6c5ce7"><Document /></el-icon>
        <span class="logo-text">{{ t('app.title') }}</span>
      </div>

      <nav class="header-nav">
        <template v-if="authStore.isAuthenticated">
          <el-button text @click="router.push({ name: 'quick-reduce' })">
            {{ t('nav.quickReduce') }}
          </el-button>
          <el-button text @click="router.push({ name: 'history' })">
            {{ t('nav.myDocuments') }}
          </el-button>
          <el-button text @click="router.push({ name: 'prompts' })">
            {{ t('nav.prompts') }}
          </el-button>
          <el-button v-if="authStore.isAdmin" text type="warning" @click="router.push({ name: 'admin' })">
            <el-icon><Setting /></el-icon>
            {{ t('nav.admin') }}
          </el-button>
          <el-dropdown trigger="click">
            <span class="user-dropdown">
              <el-icon><User /></el-icon>
              <span class="user-email">{{ authStore.userEmail }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push({ name: 'history' })">
                  <el-icon><Collection /></el-icon>{{ t('nav.myDocuments') }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="logout">
                  <el-icon><SwitchButton /></el-icon>{{ t('nav.logout') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button text @click="router.push({ name: 'quick-reduce' })">
            {{ t('nav.quickReduce') }}
          </el-button>
          <el-button text @click="router.push({ name: 'login' })">
            {{ t('nav.login') }}
          </el-button>
          <el-button type="primary" size="small" @click="router.push({ name: 'register' })">
            {{ t('nav.register') }}
          </el-button>
        </template>
        <el-button text class="locale-btn" @click="toggleLocale">
          {{ currentLocaleLabel }}
        </el-button>
      </nav>
    </div>
  </el-header>
</template>

<style scoped>
.app-header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 24px;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.header-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
  letter-spacing: -0.5px;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: #f5f7fa;
}

.user-email {
  font-size: 14px;
  color: #606266;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.locale-btn {
  margin-left: 4px;
  font-weight: 600;
  font-size: 12px;
  min-width: 36px;
}
</style>
