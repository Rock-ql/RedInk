/**
 * 用户认证状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'

export interface User {
  id: number
  username: string
  is_active: boolean
  created_at: string | null
  last_login_at: string | null
}

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const username = computed(() => user.value?.username || '')

  // 初始化：从 localStorage 恢复登录状态
  async function initAuth() {
    if (initialized.value) return

    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      token.value = savedToken

      try {
        // 验证 token 有效性
        const result = await authApi.getCurrentUser()
        if (result.success && result.user) {
          user.value = result.user
        } else {
          // token 无效，清除
          logout()
        }
      } catch (error) {
        // 请求失败，清除登录状态
        logout()
      }
    }

    initialized.value = true
  }

  // 登录
  async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    loading.value = true

    try {
      const result = await authApi.login(username, password)

      if (result.success && result.token && result.user) {
        token.value = result.token
        user.value = result.user
        localStorage.setItem('token', result.token)
        return { success: true }
      }

      return { success: false, error: result.error || '登录失败' }
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '登录失败'
      return { success: false, error: errorMsg }
    } finally {
      loading.value = false
    }
  }

  // 注册
  async function register(username: string, password: string): Promise<{ success: boolean; error?: string }> {
    loading.value = true

    try {
      const result = await authApi.register(username, password)

      if (result.success && result.token && result.user) {
        token.value = result.token
        user.value = result.user
        localStorage.setItem('token', result.token)
        return { success: true }
      }

      return { success: false, error: result.error || '注册失败' }
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message || '注册失败'
      return { success: false, error: errorMsg }
    } finally {
      loading.value = false
    }
  }

  // 登出
  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
  }

  // 刷新 token
  async function refreshToken(): Promise<boolean> {
    try {
      const result = await authApi.refreshToken()
      if (result.success && result.token) {
        token.value = result.token
        localStorage.setItem('token', result.token)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  return {
    // 状态
    user,
    token,
    loading,
    initialized,

    // 计算属性
    isAuthenticated,
    username,

    // 方法
    initAuth,
    login,
    register,
    logout,
    refreshToken
  }
})
