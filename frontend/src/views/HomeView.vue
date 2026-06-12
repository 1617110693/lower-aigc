<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

function getStarted() {
  if (authStore.isAuthenticated) {
    router.push({ name: 'upload' })
  } else {
    router.push({ name: 'register' })
  }
}

const features = [
  { icon: 'MagicStick', key: 'feature1' },
  { icon: 'Switch', key: 'feature2' },
  { icon: 'Files', key: 'feature3' },
  { icon: 'Lock', key: 'feature4' },
]
</script>

<template>
  <div class="home-page">
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">{{ t('home.hero') }}</h1>
        <p class="hero-subtitle">{{ t('home.heroSub') }}</p>
        <el-button type="primary" size="large" round class="hero-btn" @click="getStarted">
          {{ t('home.getStarted') }}
          <el-icon class="ml-2"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </section>

    <section class="features">
      <div class="features-grid">
        <div v-for="f in features" :key="f.key" class="feature-card">
          <div class="feature-icon">
            <el-icon :size="36"><component :is="f.icon" /></el-icon>
          </div>
          <h3>{{ t(`home.${f.key}Title`) }}</h3>
          <p>{{ t(`home.${f.key}Desc`) }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  padding: 80px 24px 60px;
}

.hero-content {
  max-width: 680px;
  margin: 0 auto;
}

.hero-title {
  font-size: 42px;
  font-weight: 800;
  color: #2c3e50;
  line-height: 1.3;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #6c5ce7, #a29bfe);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 18px;
  color: #606266;
  line-height: 1.7;
  margin-bottom: 36px;
}

.hero-btn {
  padding: 14px 40px;
  font-size: 17px;
  height: auto;
}

.ml-2 {
  margin-left: 6px;
}

.features {
  padding: 40px 24px 80px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
}

.feature-card {
  background: #fff;
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(108, 92, 231, 0.12);
}

.feature-icon {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: linear-gradient(135deg, #f0edff, #e8e4ff);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  color: #6c5ce7;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 10px;
}

.feature-card p {
  font-size: 14px;
  color: #909399;
  line-height: 1.6;
}
</style>
