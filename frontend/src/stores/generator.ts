import { defineStore } from 'pinia'
import type { Page } from '../api'

export interface GeneratedImage {
  index: number
  url: string
  status: 'generating' | 'done' | 'error' | 'retrying'
  error?: string
  retryable?: boolean
}

export interface GeneratorState {
  // 当前阶段
  stage: 'input' | 'outline' | 'generating' | 'result'

  // 用户输入
  topic: string

  // 大纲数据
  outline: {
    raw: string
    pages: Page[]
  }

  // 生成进度
  progress: {
    current: number
    total: number
    status: 'idle' | 'generating' | 'done' | 'error'
  }

  // 生成结果
  images: GeneratedImage[]

  // 任务ID
  taskId: string | null

  // 历史记录ID
  recordId: string | null

  // 用户上传的图片（用于图片生成参考）
  userImages: File[]

  // 待生成的页面索引列表（用于选择性生成）
  pagesToGenerate: number[]
}

const STORAGE_KEY = 'generator-state'

// 从 localStorage 加载状态
function loadState(): Partial<GeneratorState> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.error('加载状态失败:', e)
  }
  return {}
}

// 保存状态到 localStorage
function saveState(state: GeneratorState) {
  try {
    // 只保存关键数据，不保存 userImages（文件对象无法序列化）
    const toSave = {
      stage: state.stage,
      topic: state.topic,
      outline: state.outline,
      progress: state.progress,
      images: state.images,
      taskId: state.taskId,
      recordId: state.recordId
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
  } catch (e) {
    console.error('保存状态失败:', e)
  }
}

export const useGeneratorStore = defineStore('generator', {
  state: (): GeneratorState => {
    const saved = loadState()
    return {
      stage: saved.stage || 'input',
      topic: saved.topic || '',
      outline: saved.outline || {
        raw: '',
        pages: []
      },
      progress: saved.progress || {
        current: 0,
        total: 0,
        status: 'idle'
      },
      images: saved.images || [],
      taskId: saved.taskId || null,
      recordId: saved.recordId || null,
      userImages: [],  // 不从 localStorage 恢复
      pagesToGenerate: []  // 待生成的页面索引列表
    }
  },

  actions: {
    // 设置主题
    setTopic(topic: string) {
      this.topic = topic
    },

    // 设置大纲
    setOutline(raw: string, pages: Page[]) {
      this.outline.raw = raw
      this.outline.pages = pages
      this.stage = 'outline'
    },

    // 更新页面
    updatePage(index: number, content: string) {
      const page = this.outline.pages.find(p => p.index === index)
      if (page) {
        page.content = content
        // 同步更新 raw 文本
        this.syncRawFromPages()
      }
    },

    // 根据 pages 重新生成 raw 文本
    syncRawFromPages() {
      this.outline.raw = this.outline.pages
        .map(page => page.content)
        .join('\n\n<page>\n\n')
    },

    // 删除页面
    deletePage(index: number) {
      this.outline.pages = this.outline.pages.filter(p => p.index !== index)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 添加页面
    addPage(type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: this.outline.pages.length,
        type,
        content
      }
      this.outline.pages.push(newPage)
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 插入页面
    insertPage(afterIndex: number, type: 'cover' | 'content' | 'summary', content: string = '') {
      const newPage: Page = {
        index: afterIndex + 1,
        type,
        content
      }
      this.outline.pages.splice(afterIndex + 1, 0, newPage)
      // 重新索引
      this.outline.pages.forEach((page, idx) => {
        page.index = idx
      })
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 移动页面 (拖拽排序)
    movePage(fromIndex: number, toIndex: number) {
      const pages = [...this.outline.pages]
      const [movedPage] = pages.splice(fromIndex, 1)
      pages.splice(toIndex, 0, movedPage)

      // 重新索引
      pages.forEach((page, idx) => {
        page.index = idx
      })

      this.outline.pages = pages
      // 同步更新 raw 文本
      this.syncRawFromPages()
    },

    // 设置待生成的页面索引
    setPagesToGenerate(indices: number[]) {
      this.pagesToGenerate = indices
    },

    // 开始生成（支持选择性生成）
    startGeneration() {
      this.stage = 'generating'
      // 如果有指定待生成的页面，只生成这些页面；否则生成全部
      const pagesToGen = this.pagesToGenerate.length > 0
        ? this.pagesToGenerate
        : this.outline.pages.map(p => p.index)

      this.progress.current = 0
      this.progress.total = pagesToGen.length
      this.progress.status = 'generating'

      // 初始化 images 数组，只为待生成的页面创建条目
      // 保留已有的图片数据（用于增量生成场景）
      const existingImages = new Map(this.images.map(img => [img.index, img]))

      this.images = this.outline.pages.map(page => {
        if (pagesToGen.includes(page.index)) {
          // 需要生成的页面，设为 generating 状态
          return {
            index: page.index,
            url: '',
            status: 'generating' as const
          }
        } else {
          // 不需要生成的页面，保留原有数据或设为空
          const existing = existingImages.get(page.index)
          return existing || {
            index: page.index,
            url: '',
            status: 'done' as const  // 标记为已完成（跳过）
          }
        }
      })
    },

    // 获取待生成的页面列表
    getPagesToGenerate() {
      const indices = this.pagesToGenerate.length > 0
        ? this.pagesToGenerate
        : this.outline.pages.map(p => p.index)
      return this.outline.pages.filter(p => indices.includes(p.index))
    },

    // 更新进度
    updateProgress(index: number, status: 'generating' | 'done' | 'error', url?: string, error?: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = status
        if (url) image.url = url
        if (error) image.error = error
      }
      if (status === 'done') {
        this.progress.current++
      }
    },

    updateImage(index: number, newUrl: string) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        const timestamp = Date.now()
        image.url = `${newUrl}?t=${timestamp}`
        image.status = 'done'
        delete image.error
      }
    },

    // 完成生成
    finishGeneration(taskId: string) {
      this.taskId = taskId
      this.stage = 'result'
      this.progress.status = 'done'
    },

    // 设置单个图片为重试中状态
    setImageRetrying(index: number) {
      const image = this.images.find(img => img.index === index)
      if (image) {
        image.status = 'retrying'
      }
    },

    // 获取失败的图片列表
    getFailedImages() {
      return this.images.filter(img => img.status === 'error')
    },

    // 获取失败图片对应的页面
    getFailedPages() {
      const failedIndices = this.images
        .filter(img => img.status === 'error')
        .map(img => img.index)
      return this.outline.pages.filter(page => failedIndices.includes(page.index))
    },

    // 检查是否有失败的图片
    hasFailedImages() {
      return this.images.some(img => img.status === 'error')
    },

    // 重置
    reset() {
      this.stage = 'input'
      this.topic = ''
      this.outline = {
        raw: '',
        pages: []
      }
      this.progress = {
        current: 0,
        total: 0,
        status: 'idle'
      }
      this.images = []
      this.taskId = null
      this.recordId = null
      this.userImages = []
      this.pagesToGenerate = []
      // 清除 localStorage
      localStorage.removeItem(STORAGE_KEY)
    },

    // 保存当前状态
    saveToStorage() {
      saveState(this)
    }
  }
})

// 监听状态变化并自动保存（使用 watch）
import { watch } from 'vue'

export function setupAutoSave() {
  const store = useGeneratorStore()

  // 监听关键字段变化并自动保存
  watch(
    () => ({
      stage: store.stage,
      topic: store.topic,
      outline: store.outline,
      progress: store.progress,
      images: store.images,
      taskId: store.taskId,
      recordId: store.recordId
    }),
    () => {
      store.saveToStorage()
    },
    { deep: true }
  )
}
