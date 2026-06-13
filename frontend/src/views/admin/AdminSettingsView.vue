<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getEnvConfig, updateEnvConfig } from '@/api/admin'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)
const rawContent = ref('')
const form = ref({})
const adminEmailsList = ref([])  // 独立维护管理员邮箱数组，便于 tag 输入

// ── 解析/序列化管理员邮箱 JSON 数组 ──────────────────────────────────────────

function parseAdminEmails(raw) {
  if (!raw || raw === '[]') return []
  try {
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr.filter((e) => typeof e === 'string' && e.trim()) : []
  } catch {
    return []
  }
}

// ── 加载配置 ────────────────────────────────────────────────────────────────

async function loadConfig() {
  loading.value = true
  try {
    const res = await getEnvConfig()
    rawContent.value = res.data.content
    form.value = { ...res.data.settings }
    adminEmailsList.value = parseAdminEmails(form.value.ADMIN_EMAILS)
  } catch {
    ElMessage.error(t('admin.loadError'))
  } finally {
    loading.value = false
  }
}

// ── 保存配置 ────────────────────────────────────────────────────────────────

async function handleSave() {
  // 将管理员邮箱数组序列化为 JSON 字符串
  const toSave = { ...form.value }
  toSave.ADMIN_EMAILS = JSON.stringify(adminEmailsList.value.filter((e) => e.trim()))

  try {
    await ElMessageBox.confirm(
      t('admin.saveConfirm'),
      t('admin.saveTitle'),
      { confirmButtonText: t('common.ok'), cancelButtonText: t('common.cancel'), type: 'warning' },
    )
  } catch {
    return
  }
  saving.value = true
  try {
    const res = await updateEnvConfig(toSave)
    rawContent.value = res.data.content
    ElMessage.success(t('admin.saveSuccess'))
  } catch {
    ElMessage.error(t('admin.saveError'))
  } finally {
    saving.value = false
  }
}

// ── 布尔值处理 ──────────────────────────────────────────────────────────────

function boolToStr(val) {
  return val === 'true' || val === true ? 'true' : 'false'
}

function setBool(key, val) {
  form.value[key] = val ? 'true' : 'false'
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="admin-settings-page">
    <div class="page-header">
      <h1>{{ t('admin.title') }}</h1>
      <p>{{ t('admin.desc') }}</p>
    </div>

    <div v-loading="loading" class="settings-container">
      <!-- 应用基础配置 -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionApp') }}</span>
        </template>
        <el-form :model="form" label-position="top" label-width="auto">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('admin.environment')">
                <el-select v-model="form.ENVIRONMENT" class="full-width">
                  <el-option label="development" value="development" />
                  <el-option label="production" value="production" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.secretKey')">
                <el-input v-model="form.SECRET_KEY" show-password />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('admin.appName')">
                <el-input v-model="form.APP_NAME" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.appUrl')">
                <el-input v-model="form.APP_URL" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 数据库 -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionDb') }}</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-form-item :label="t('admin.databaseUrl')">
            <el-input v-model="form.DATABASE_URL" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- DeepSeek API -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionDeepseek') }}</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('admin.deepseekApiKey')">
                <el-input v-model="form.DEEPSEEK_API_KEY" show-password />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.deepseekBaseUrl')">
                <el-input v-model="form.DEEPSEEK_BASE_URL" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 邮件 SMTP -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionSmtp') }}</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item :label="t('admin.smtpHost')">
                <el-input v-model="form.SMTP_HOST" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item :label="t('admin.smtpPort')">
                <el-input v-model="form.SMTP_PORT" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.smtpUser')">
                <el-input v-model="form.SMTP_USER" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('admin.smtpPassword')">
                <el-input v-model="form.SMTP_PASSWORD" show-password />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="t('admin.smtpFrom')">
                <el-input v-model="form.SMTP_FROM" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item :label="t('admin.smtpTls')">
                <el-switch
                  :model-value="form.SMTP_USE_TLS === 'true'"
                  @change="(v) => setBool('SMTP_USE_TLS', v)"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 认证 -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionAuth') }}</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item :label="t('admin.jwtExpire')">
                <el-input v-model="form.ACCESS_TOKEN_EXPIRE_MINUTES" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item :label="t('admin.requireEmailVerify')">
                <el-switch
                  :model-value="form.REQUIRE_EMAIL_VERIFICATION === 'true'"
                  @change="(v) => setBool('REQUIRE_EMAIL_VERIFICATION', v)"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.adminEmails')">
                <el-select
                  v-model="adminEmailsList"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  :placeholder="t('admin.adminEmailsPlaceholder')"
                  class="full-width"
                >
                  <el-option
                    v-for="email in adminEmailsList"
                    :key="email"
                    :label="email"
                    :value="email"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 上传限制 -->
      <el-card class="settings-card">
        <template #header>
          <span class="card-title">{{ t('admin.sectionUpload') }}</span>
        </template>
        <el-form :model="form" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="t('admin.maxUploadMb')">
                <el-input v-model="form.MAX_UPLOAD_SIZE_MB" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('admin.maxParagraphs')">
                <el-input v-model="form.MAX_PARAGRAPHS_PER_DOC" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 保存按钮 -->
      <div class="save-bar">
        <el-button type="primary" size="large" :loading="saving" @click="handleSave">
          {{ t('common.save') }}
        </el-button>
        <span class="save-hint">{{ t('admin.restartHint') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-settings-page {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 60px;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 6px;
}

.page-header p {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-card {
  border-radius: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
}

.full-width {
  width: 100%;
}

.settings-card :deep(.el-form-item) {
  margin-bottom: 4px;
}

.save-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
}

.save-hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
