/**
 * 认证相关 API
 */
import axios from 'axios'

const API_BASE_URL = '/api'

export interface User {
  id: number
  username: string
  is_active: boolean
  created_at: string | null
  last_login_at: string | null
}

export interface AuthResponse {
  success: boolean
  user?: User
  token?: string
  error?: string
}

// 注册
export async function register(username: string, password: string): Promise<AuthResponse> {
  const response = await axios.post(`${API_BASE_URL}/auth/register`, {
    username,
    password
  })
  return response.data
}

// 登录
export async function login(username: string, password: string): Promise<AuthResponse> {
  const response = await axios.post(`${API_BASE_URL}/auth/login`, {
    username,
    password
  })
  return response.data
}

// 登出
export async function logout(): Promise<{ success: boolean; message?: string }> {
  const response = await axios.post(`${API_BASE_URL}/auth/logout`)
  return response.data
}

// 获取当前用户信息
export async function getCurrentUser(): Promise<{ success: boolean; user?: User; error?: string }> {
  const response = await axios.get(`${API_BASE_URL}/auth/me`)
  return response.data
}

// 刷新 Token
export async function refreshToken(): Promise<{ success: boolean; token?: string; error?: string }> {
  const response = await axios.post(`${API_BASE_URL}/auth/refresh`)
  return response.data
}
