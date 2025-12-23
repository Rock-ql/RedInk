<template>
  <div class="container" style="max-width: 100%;">
    <div class="page-header" style="max-width: 1200px; margin: 0 auto 30px auto;">
      <div>
        <h1 class="page-title">{{ store.outlineGenerating ? '正在生成大纲...' : '编辑大纲' }}</h1>
        <p class="page-subtitle">
          <span v-if="store.outlineGenerating" class="generating-text">
            AI 正在为您构思内容框架<span class="typing-cursor">|</span>
          </span>
          <span v-else>调整页面顺序，修改文案，打造完美内容</span>
        </p>
      </div>
      <div style="display: flex; gap: 12px;">
        <button class="btn btn-secondary" @click="goBack" style="background: white; border: 1px solid var(--border-color);">
          上一步
        </button>
        <button
          v-if="store.outline.pages.length === 0 && !store.outlineGenerating"
          class="btn btn-primary"
          @click="regenerateOutline"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;">
            <path d="M23 4v6h-6"></path>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          重新生成大纲
        </button>
        <button
          v-else
          class="btn btn-primary"
          @click="generateAll"
          :disabled="store.outlineGenerating || store.outline.pages.length === 0"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg>
          一键生成全部
        </button>
      </div>
    </div>

    <!-- 生成中状态 -->
    <div v-if="store.outlineGenerating" class="outline-grid">
      <div class="card outline-card generating-card">
        <div class="generating-placeholder">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="generating-hint">正在生成大纲...</div>
        </div>
      </div>
    </div>

    <!-- 空状态 - 大纲为空且不在生成中 -->
    <div v-else-if="store.outline.pages.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ddd" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="12" y1="11" x2="12" y2="17"></line>
          <line x1="9" y1="14" x2="15" y2="14"></line>
        </svg>
      </div>
      <h3 class="empty-title">暂无大纲内容</h3>
      <p class="empty-desc">点击下方按钮为「{{ store.topic || '未知主题' }}」生成大纲</p>
      <button class="btn btn-primary btn-lg" @click="regenerateOutline">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
          <path d="M23 4v6h-6"></path>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        生成大纲
      </button>
    </div>

    <!-- 已生成的大纲 -->
    <div v-else class="outline-grid">
      <div
        v-for="(page, idx) in store.outline.pages"
        :key="page.index"
        class="card outline-card"
        :draggable="true"
        @dragstart="onDragStart($event, idx)"
        @dragover.prevent="onDragOver($event, idx)"
        @drop="onDrop($event, idx)"
        :class="{ 'dragging-over': dragOverIndex === idx }"
      >
        <!-- 拖拽手柄 (改为右上角或更加隐蔽) -->
        <div class="card-top-bar">
          <div class="page-info">
             <span class="page-number">P{{ idx + 1 }}</span>
             <span class="page-type" :class="page.type">{{ getPageTypeName(page.type) }}</span>
          </div>

          <div class="card-controls">
            <button class="icon-btn refresh-btn" @click="regeneratePageContent(page.index)" title="重新生成此页文案">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                 <path d="M23 4v6h-6"></path>
                 <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
               </svg>
            </button>
            <div class="drag-handle" title="拖拽排序">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>
            </div>
            <button class="icon-btn delete-btn" @click="deletePage(idx)" title="删除此页">
               <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
        </div>

        <textarea
          v-model="page.content"
          class="textarea-paper"
          placeholder="在此输入文案..."
          @input="store.updatePage(page.index, page.content)"
        />

        <div class="card-bottom-bar">
          <div class="word-count">{{ page.content.length }} 字</div>
          <button class="generate-btn" @click="generateSingle(page.index)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
              <line x1="16" y1="8" x2="2" y2="22"></line>
            </svg>
            生成
          </button>
        </div>
      </div>

      <!-- 添加按钮卡片 -->
      <div class="card add-card-dashed" @click="addPage('content')">
        <div class="add-content">
          <div class="add-icon">+</div>
          <span>添加页面</span>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      {{ error }}
    </div>

    <div style="height: 100px;"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { generateOutline, createHistory, updateHistory } from '../api'

const router = useRouter()
const store = useGeneratorStore()

const dragOverIndex = ref<number | null>(null)
const draggedIndex = ref<number | null>(null)
const error = ref('')
const saveTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const isSaving = ref(false)

const getPageTypeName = (type: string) => {
  const names = {
    cover: '封面',
    content: '内容',
    summary: '总结'
  }
  return names[type as keyof typeof names] || '内容'
}

// 保存大纲到历史记录（防抖）
const saveOutline = async () => {
  if (!store.recordId || store.outlineGenerating) return

  isSaving.value = true
  try {
    await updateHistory(store.recordId, {
      outline: {
        raw: store.outline.raw,
        pages: store.outline.pages
      }
    })
    console.log('大纲已自动保存')
  } catch (e) {
    console.error('自动保存失败:', e)
  } finally {
    isSaving.value = false
  }
}

// 防抖保存
const debouncedSave = () => {
  if (saveTimer.value) {
    clearTimeout(saveTimer.value)
  }
  saveTimer.value = setTimeout(() => {
    saveOutline()
  }, 1000)  // 1秒防抖
}

// 监听大纲变化，自动保存
watch(
  () => store.outline,
  () => {
    if (store.recordId && !store.outlineGenerating) {
      debouncedSave()
    }
  },
  { deep: true }
)

// 拖拽逻辑
const onDragStart = (e: DragEvent, index: number) => {
  draggedIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.dropEffect = 'move'
  }
}

const onDragOver = (e: DragEvent, index: number) => {
  if (draggedIndex.value === index) return
  dragOverIndex.value = index
}

const onDrop = (e: DragEvent, index: number) => {
  dragOverIndex.value = null
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    store.movePage(draggedIndex.value, index)
  }
  draggedIndex.value = null
}

const deletePage = (index: number) => {
  if (confirm('确定要删除这一页吗？')) {
    store.deletePage(index)
  }
}

const addPage = (type: 'cover' | 'content' | 'summary') => {
  store.addPage(type, '')
  // 滚动到底部
  nextTick(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  })
}

const goBack = () => {
  // 如果正在生成，则停止
  store.outlineGenerating = false
  // 离开前保存
  if (store.recordId && saveTimer.value) {
    clearTimeout(saveTimer.value)
    saveOutline()
  }
  router.back()
}

// 生成全部页面
const generateAll = () => {
  store.setPagesToGenerate([])  // 空数组表示生成全部
  router.push('/generate')
}

// 生成单个页面
const generateSingle = (pageIndex: number) => {
  store.setPagesToGenerate([pageIndex])
  router.push('/generate')
}

// 重新生成整个大纲
const regenerateOutline = async () => {
  if (!store.topic) {
    error.value = '缺少主题，无法重新生成'
    return
  }

  // 标记为生成中
  store.outlineGenerating = true
  error.value = ''

  try {
    const result = await generateOutline(
      store.topic,
      store.userImages.length > 0 ? store.userImages : undefined
    )

    if (result.success && result.pages) {
      store.setOutline(result.outline || '', result.pages)

      // 更新历史记录
      if (store.recordId) {
        try {
          await updateHistory(store.recordId, {
            outline: {
              raw: result.outline || '',
              pages: result.pages
            }
          })
          console.log('大纲已更新到历史记录')
        } catch (e) {
          console.error('更新历史记录失败:', e)
        }
      }
    } else {
      error.value = result.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    store.outlineGenerating = false
  }
}

// 重新生成单页文案（重新生成整个大纲，但只替换指定页）
const regeneratePageContent = async (pageIndex: number) => {
  if (!store.topic) {
    error.value = '缺少主题，无法重新生成'
    return
  }

  if (!confirm('将重新生成整个大纲，此操作会更新所有页面的文案内容。确定继续吗？')) {
    return
  }

  await regenerateOutline()
}

// 页面加载时检查是否需要生成大纲
onMounted(async () => {
  // 如果没有主题，返回首页
  if (!store.topic) {
    router.push('/')
    return
  }

  // 如果需要生成大纲
  if (store.outlineGenerating) {
    error.value = ''

    // 先创建草稿记录
    try {
      const historyResult = await createHistory(store.topic, {
        raw: '',
        pages: []
      })
      if (historyResult.success && historyResult.record_id) {
        store.recordId = historyResult.record_id
        console.log('创建草稿记录:', store.recordId)
      }
    } catch (e) {
      console.error('创建草稿记录失败:', e)
    }

    // 开始生成大纲
    try {
      const result = await generateOutline(
        store.topic,
        store.userImages.length > 0 ? store.userImages : undefined
      )

      if (result.success && result.pages) {
        store.setOutline(result.outline || '', result.pages)

        // 更新历史记录，保存生成的大纲内容
        if (store.recordId) {
          try {
            await updateHistory(store.recordId, {
              outline: {
                raw: result.outline || '',
                pages: result.pages
              },
              status: 'draft'
            })
            console.log('大纲已保存到历史记录')
          } catch (e) {
            console.error('更新历史记录失败:', e)
          }
        }
      } else {
        error.value = result.error || '生成大纲失败'
      }
    } catch (err: any) {
      error.value = err.message || '网络错误，请重试'
    } finally {
      store.outlineGenerating = false
    }
  }
})
</script>

<style scoped>
/* 网格布局 */
.outline-grid {
  display: grid;
  /* 响应式列：最小宽度 280px，自动填充 */
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
}

.outline-card {
  display: flex;
  flex-direction: column;
  padding: 16px; /* 减小内边距 */
  transition: all 0.2s ease;
  border: none;
  border-radius: 8px; /* 较小的圆角 */
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  /* 保持一定的长宽比感，虽然高度自适应，但由于 flex column 和内容撑开，
     这里设置一个 min-height 让它看起来像个竖向卡片 */
  min-height: 360px; 
  position: relative;
}

.outline-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  z-index: 10;
}

.outline-card.dragging-over {
  border: 2px dashed var(--primary);
  opacity: 0.8;
}

/* 顶部栏 */
.card-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-number {
  font-size: 14px;
  font-weight: 700;
  color: #ccc;
  font-family: 'Inter', sans-serif;
}

.page-type {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.page-type.cover { color: #FF4D4F; background: #FFF1F0; }
.page-type.content { color: #8c8c8c; background: #f5f5f5; }
.page-type.summary { color: #52C41A; background: #F6FFED; }

.card-controls {
  display: flex;
  gap: 8px;
  opacity: 0.4;
  transition: opacity 0.2s;
}
.outline-card:hover .card-controls { opacity: 1; }

.drag-handle {
  cursor: grab;
  padding: 2px;
}
.drag-handle:active { cursor: grabbing; }

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 2px;
  transition: color 0.2s;
}
.icon-btn.delete-btn:hover { color: #FF4D4F; }
.icon-btn.refresh-btn:hover { color: var(--primary); }

/* 文本区域 - 核心 */
.textarea-paper {
  flex: 1; /* 占据剩余空间 */
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 16px; /* 更大的字号 */
  line-height: 1.7; /* 舒适行高 */
  color: #333;
  resize: none; /* 禁止手动拉伸，保持卡片整体感 */
  font-family: inherit;
  margin-bottom: 10px;
}

.textarea-paper:focus {
  outline: none;
}

.word-count {
  text-align: right;
  font-size: 11px;
  color: #ddd;
}

/* 底部栏 */
.card-bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0;
}

.outline-card:hover .generate-btn {
  opacity: 1;
}

.generate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.generate-btn:active {
  transform: translateY(0);
}

/* 添加卡片 */
.add-card-dashed {
  border: 2px dashed #eee;
  background: transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 360px;
  color: #ccc;
  transition: all 0.2s;
}

.add-card-dashed:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(255, 36, 66, 0.02);
}

.add-content {
  text-align: center;
}

.add-icon {
  font-size: 32px;
  font-weight: 300;
  margin-bottom: 8px;
}

/* 生成中状态 */
.generating-text {
  color: var(--primary);
}

.typing-cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.generating-card {
  background: linear-gradient(135deg, rgba(255, 77, 79, 0.05) 0%, rgba(255, 77, 79, 0.02) 100%);
  border: 2px dashed rgba(255, 77, 79, 0.2);
}

.generating-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  gap: 16px;
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.generating-hint {
  color: #999;
  font-size: 14px;
}

/* 错误提示 */
.error-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: #FF4D4F;
  color: white;
  padding: 12px 24px;
  border-radius: 50px;
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translate(-50%, 20px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 24px;
  opacity: 0.6;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px 0;
}

.empty-desc {
  font-size: 14px;
  color: #999;
  margin: 0 0 32px 0;
  max-width: 300px;
}

.btn-lg {
  padding: 14px 32px;
  font-size: 15px;
}
</style>
