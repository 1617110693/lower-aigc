<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <span>&copy; 2026 {{ t('app.title') }}. All rights reserved.</span>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  background: #fff;
  border-top: 1px solid #ebeef5;
  padding: 16px 24px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}

.footer-inner {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
