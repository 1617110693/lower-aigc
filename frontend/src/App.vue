<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useAppStore } from '@/stores/app'

const { locale } = useI18n()
const appStore = useAppStore()
const route = useRoute()

const elLocale = computed(() => (appStore.locale === 'en' ? en : zhCn))

const hideLayout = computed(() => {
  return route.name === 'login' || route.name === 'register'
})
</script>

<template>
  <el-config-provider :locale="elLocale">
    <div class="app-container">
      <AppHeader v-if="!hideLayout" />
      <main class="main-content" :class="{ 'no-padding': hideLayout }">
        <router-view />
      </main>
      <AppFooter v-if="!hideLayout" />
    </div>
  </el-config-provider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
  color: #2c3e50;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
  width: 100%;
}

.main-content.no-padding {
  padding: 0;
  max-width: none;
}

/* Element Plus overrides */
.el-button--primary {
  --el-button-bg-color: #6c5ce7;
  --el-button-border-color: #6c5ce7;
  --el-button-hover-bg-color: #7c6ff7;
  --el-button-hover-border-color: #7c6ff7;
}

:root {
  --el-color-primary: #6c5ce7;
  --el-color-primary-light-3: #8b7ff0;
}
</style>
