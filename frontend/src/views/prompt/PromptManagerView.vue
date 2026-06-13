<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listCustomPrompts,
  createCustomPrompt,
  updateCustomPrompt,
  deleteCustomPrompt,
} from '@/api/prompt'
import { getPrompts } from '@/api/document'

const { t } = useI18n()

const builtinPrompts = ref([])
const customPrompts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const hasBuiltin = computed(() => builtinPrompts.value.length > 0)

const defaultForm = () => ({
  name: '',
  description: '',
  system_content: '',
})

const form = ref(defaultForm())

// ── 加载列表 ────────────────────────────────────────────────────────────────

async function loadPrompts() {
  loading.value = true
  try {
    // 并行拉取内置策略（含 system_content）和自定义策略
    const [promptsRes, customRes] = await Promise.all([
      getPrompts(),
      listCustomPrompts(),
    ])
    builtinPrompts.value = (promptsRes.data || []).filter((p) => p.system_default)
    customPrompts.value = customRes.data || []
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

// ── 打开对话框 ──────────────────────────────────────────────────────────────

function openCreate() {
  isEditing.value = false
  editingId.value = null
  form.value = defaultForm()
  dialogVisible.value = true
}

function openEdit(prompt) {
  isEditing.value = true
  editingId.value = prompt.id
  form.value = {
    name: prompt.name,
    description: prompt.description,
    system_content: prompt.system_content,
  }
  dialogVisible.value = true
}

// ── 保存 ────────────────────────────────────────────────────────────────────

async function handleSave() {
  if (!form.value.name.trim() || !form.value.system_content.trim()) {
    ElMessage.warning(t('prompts.fillRequired'))
    return
  }
  try {
    if (isEditing.value) {
      await updateCustomPrompt(editingId.value, {
        name: form.value.name,
        description: form.value.description,
        system_content: form.value.system_content,
      })
      ElMessage.success(t('prompts.updateSuccess'))
    } else {
      await createCustomPrompt({
        name: form.value.name,
        description: form.value.description,
        system_content: form.value.system_content,
      })
      ElMessage.success(t('prompts.createSuccess'))
    }
    dialogVisible.value = false
    await loadPrompts()
  } catch {
    // error handled by interceptor
  }
}

// ── 删除 ────────────────────────────────────────────────────────────────────

async function handleDelete(prompt) {
  try {
    await ElMessageBox.confirm(
      t('prompts.deleteConfirm', { name: prompt.name }),
      '',
      { confirmButtonText: t('common.ok'), cancelButtonText: t('common.cancel'), type: 'warning' },
    )
    await deleteCustomPrompt(prompt.id)
    ElMessage.success(t('prompts.deleteSuccess'))
    await loadPrompts()
  } catch {
    // cancelled or error
  }
}

onMounted(() => {
  loadPrompts()
})
</script>

<template>
  <div class="prompt-manager-page">
    <div class="page-header">
      <div>
        <h1>{{ t('prompts.title') }}</h1>
        <p>{{ t('prompts.desc') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        {{ t('prompts.create') }}
      </el-button>
    </div>

    <!-- 内置策略列表（只读） -->
    <div v-if="hasBuiltin" class="section-label">{{ t('prompts.builtinTitle') }}</div>
    <div v-if="hasBuiltin" class="prompt-list">
      <el-card v-for="p in builtinPrompts" :key="p.id" class="prompt-card builtin-card" shadow="hover">
        <div class="prompt-card-header">
          <div class="prompt-card-title">
            <span class="prompt-name">{{ p.name }}</span>
            <el-tag size="small" type="primary">{{ t('prompts.builtin') }}</el-tag>
          </div>
        </div>
        <p v-if="p.description" class="prompt-desc">{{ p.description }}</p>
        <div v-if="p.system_content" class="prompt-content">
          <el-input
            :model-value="p.system_content"
            type="textarea"
            :rows="4"
            readonly
            resize="none"
          />
        </div>
      </el-card>
    </div>

    <!-- 自定义策略列表 -->
    <div v-if="hasBuiltin" class="section-label">{{ t('prompts.customTitle') }}</div>
    <div v-loading="loading" class="prompt-list">
      <el-empty v-if="!loading && !customPrompts.length" :description="t('prompts.empty')" />

      <el-card v-for="p in customPrompts" :key="p.id" class="prompt-card" shadow="hover">
        <div class="prompt-card-header">
          <div class="prompt-card-title">
            <span class="prompt-name">{{ p.name }}</span>
            <el-tag v-if="!p.is_active" size="small" type="info">{{ t('prompts.disabled') }}</el-tag>
            <el-tag v-else size="small" type="warning">{{ t('prompts.custom') }}</el-tag>
          </div>
          <div class="prompt-card-actions">
            <el-button text size="small" @click="openEdit(p)">
              <el-icon><Edit /></el-icon>
              {{ t('common.edit') }}
            </el-button>
            <el-button text size="small" type="danger" @click="handleDelete(p)">
              <el-icon><Delete /></el-icon>
              {{ t('common.delete') }}
            </el-button>
          </div>
        </div>
        <p v-if="p.description" class="prompt-desc">{{ p.description }}</p>
        <div class="prompt-content">
          <el-input
            :model-value="p.system_content"
            type="textarea"
            :rows="3"
            readonly
            resize="none"
          />
        </div>
        <div class="prompt-meta">
          <span>{{ new Date(p.created_at).toLocaleDateString() }}</span>
        </div>
      </el-card>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? t('prompts.edit') : t('prompts.create')"
      width="600px"
      destroy-on-close
    >
      <el-form :model="form" label-position="top">
        <el-form-item :label="t('prompts.name')" required>
          <el-input v-model="form.name" :placeholder="t('prompts.namePlaceholder')" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('prompts.description')">
          <el-input v-model="form.description" :placeholder="t('prompts.descPlaceholder')" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('prompts.systemContent')" required>
          <el-input
            v-model="form.system_content"
            type="textarea"
            :placeholder="t('prompts.contentPlaceholder')"
            :rows="8"
            maxlength="10000"
            show-word-limit
            resize="vertical"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.prompt-manager-page {
  max-width: 900px;
  margin: 0 auto;
  padding-bottom: 60px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
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

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prompt-card {
  border-radius: 12px;
}

.prompt-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.prompt-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.prompt-name {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.prompt-desc {
  font-size: 13px;
  color: #909399;
  margin: 0 0 10px;
}

.prompt-content :deep(.el-textarea__inner) {
  font-size: 12px;
  color: #606266;
  background: #fafafa;
}

.prompt-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #c0c4cc;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.builtin-card {
  border-left: 3px solid #6c5ce7;
}

.builtin-card .prompt-content :deep(.el-textarea__inner) {
  color: #606266;
  background: #f5f7fa;
}
</style>
