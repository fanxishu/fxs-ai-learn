import Taro from '@tarojs/taro'
import type {
  ApiResponse,
  QuizGenerateRequest,
  QuizGenerateResult,
  ReportGenerateRequest,
  ReportGenerateResult,
} from '@/types/quiz'
import { ErrorCode, ERROR_TOAST } from '@/types/common'
import type {
  UserLoginResponse,
  UserProfileResponse,
  UpdateProfileRequest,
  QuizHistoryListResponse,
  QuizDetailResponse,
} from '@/types/user'
import { useUserStore } from '@/store/user'

const getEnv = (key: string, fallback: string = ''): string => {
  try {
    if (typeof process !== 'undefined' && (process as any).env && (process as any).env[key] != null) {
      return String((process as any).env[key])
    }
  } catch (_) { /* noop */ }
  return fallback
}

const BASE_URL = getEnv('TARO_APP_API_BASE', 'http://127.0.0.1:8000')
const API_PREFIX = '/api/v1'

export const getAvatarUrl = (path: string = ''): string => {
  if (/^https?:\/\//i.test(path)) return path
  if (path.startsWith(`${API_PREFIX}/user/avatars/`)) {
    return `${BASE_URL.replace(/\/$/, '')}${path}`
  }
  return ''
}

export const AUTH_TOKEN_KEY = 'auth_token'

export const getAuthToken = (): string => {
  try {
    const fromStorage = Taro.getStorageSync(AUTH_TOKEN_KEY) as string || ''
    if (fromStorage) return fromStorage
  } catch (_) { /* noop */ }
  try {
    const fromStore = useUserStore.getState().token
    if (fromStore) return fromStore
  } catch (_) { /* noop */ }
  return ''
}

export const setAuthToken = (token: string): void => {
  try { Taro.setStorageSync(AUTH_TOKEN_KEY, token) } catch (_) { /* noop */ }
}

export const clearAuthToken = (): void => {
  try { Taro.removeStorageSync(AUTH_TOKEN_KEY) } catch (_) { /* noop */ }
}

let _tokenClearedToast = false
let _redirecting = false
const dispatchUnauthCleanup = (code: number) => {
  if (
    code !== ErrorCode.UNAUTHORIZED
    && code !== ErrorCode.TOKEN_EXPIRED
    && code !== ErrorCode.NOT_LOGGED_IN
  ) return
  try { useUserStore.getState().clearAuth() } catch (_) { /* noop */ }
  if (!_tokenClearedToast) {
    _tokenClearedToast = true
    try {
      Taro.showToast({ title: ERROR_TOAST[code] || '请重新登录', icon: 'none', duration: 1800 })
    } catch (_) { /* noop */ }
    setTimeout(() => { _tokenClearedToast = false }, 2000)
  }
  if (!_redirecting) {
    _redirecting = true
    try {
      Taro.redirectTo({ url: '/pages/index/index' })
    } catch (_) { /* noop */ }
    setTimeout(() => { _redirecting = false }, 1200)
  }
}

/**
 * 把后端返回的 code 映射到用户可读 Toast 文案。
 * Task10：覆盖 3001/5001/5002/5003/Network Error 5 种分支。
 */
function codeToToast(code: number, fallback: string): string {
  if (code === 0) return ''
  // 优先用 ERROR_TOAST 表
  if (ERROR_TOAST[code]) return ERROR_TOAST[code]
  // 按区间兜底
  if (code >= 1000 && code < 2000) return fallback || '请求参数有误，请检查输入'
  if (code >= 2000 && code < 3000) return fallback || '登录状态异常，请重新登录'
  if (code >= 3000 && code < 4000) return ERROR_TOAST[ErrorCode.INPUT_CONTENT_VIOLATION]
  if (code >= 4000 && code < 5000) return fallback || '业务处理失败，请稍后重试'
  if (code >= 5000 && code < 6000) return ERROR_TOAST[ErrorCode.DEEPSEEK_RETRY_EXHAUSTED]
  return fallback || '请求失败，请稍后重试'
}

export async function request<T = unknown>(
  path: string,
  data?: unknown,
  method: 'GET' | 'POST' | 'PUT' = 'POST',
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${API_PREFIX}${path}`
  const fromStorage = (() => { try { return Taro.getStorageSync(AUTH_TOKEN_KEY) as string || '' } catch (_) { return '' } })()
  const fromStore = (() => { try { return useUserStore.getState().token || '' } catch (_) { return '' } })()
  const token = getAuthToken()
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) header['Authorization'] = `Bearer ${token}`
  console.log(`[API] ${method} ${url} token_in_headers=${!!token} len=${token.length}| storage_len=${fromStorage.length} store_len=${fromStore.length} | header_keys=${JSON.stringify(Object.keys(header))}`, data)

  try {
    const res = await Taro.request<ApiResponse<T>>({
      url,
      method,
      data,
      header,
      timeout: 30000,
    })
    const body = res.data ?? ({} as ApiResponse<T>)
    if (typeof body.code !== 'number') {
      body.code = ErrorCode.INTERNAL_SERVER_ERROR
      body.message = body.message || '服务返回格式异常'
    }
    dispatchUnauthCleanup(body.code)
    console.log(`[API] ${url} -> code=${body.code} msg=${body.message}`)
    return body
  } catch (err: unknown) {
    console.error(`[API] ${url} 网络异常:`, err)
    const msg = err instanceof Error ? err.message : 'Network Error'
    const code: number =
      /timeout/i.test(msg) ? ErrorCode.DEEPSEEK_TIMEOUT
      : ErrorCode.INTERNAL_SERVER_ERROR
    return {
      code,
      message: code === ErrorCode.DEEPSEEK_TIMEOUT
        ? ERROR_TOAST[ErrorCode.DEEPSEEK_TIMEOUT]
        : '网络请求失败，请检查网络后重试',
    } as ApiResponse<T>
  }
}

export function toastError(msg: string): void {
  Taro.showToast({ title: msg, icon: 'none', duration: 2000 })
}

/**
 * generateQuiz 统一失败处理：Task10 覆盖 3001/5001/5002/5003/Network 5 种 Toast。
 * 只在确定最终走 fallback mock 之前 Toast 一次（避免重复弹）
 */
export const API = {
  async generateQuiz(payload: QuizGenerateRequest): Promise<ApiResponse<QuizGenerateResult>> {
    const res = await request<QuizGenerateResult>('/quiz/generate', payload)
    if (res.code === 0 && res.data) return res
    const toast = codeToToast(res.code, res.message || '生成失败，请重试')
    if (toast) toastError(toast)
    console.error('[API] generateQuiz 失败 code=', res.code, 'msg=', res.message)
    return res
  },

  async generateReport(
    payload: ReportGenerateRequest,
  ): Promise<ApiResponse<ReportGenerateResult>> {
    const res = await request<ReportGenerateResult>('/report/generate', payload)
    if (res.code === 0 && res.data) return res
    const toast = codeToToast(res.code, res.message || '生成报告失败，请重试')
    if (toast) toastError(toast)
    console.error('[API] generateReport 失败 code=', res.code, 'msg=', res.message)
    return res
  },

  async loginWx(code: string): Promise<ApiResponse<UserLoginResponse>> {
    return request<UserLoginResponse>('/user/login', { code })
  },

  async getProfile(): Promise<ApiResponse<UserProfileResponse>> {
    return request<UserProfileResponse>('/user/profile', undefined, 'GET')
  },

  async updateProfile(payload: UpdateProfileRequest): Promise<ApiResponse<UserProfileResponse>> {
    return request<UserProfileResponse>('/user/profile', payload, 'PUT')
  },

  async uploadAvatar(filePath: string): Promise<ApiResponse<{ avatar_url: string }>> {
    const token = getAuthToken()
    if (!token) {
      dispatchUnauthCleanup(ErrorCode.NOT_LOGGED_IN)
      return { code: ErrorCode.NOT_LOGGED_IN, message: '请先登录后再修改头像' }
    }
    try {
      const res = await Taro.uploadFile({
        url: `${BASE_URL}${API_PREFIX}/user/avatar`,
        filePath,
        name: 'file',
        // Let uploadFile generate the multipart boundary.
        header: { Authorization: `Bearer ${token}` },
        timeout: 30000,
      })
      if (res.statusCode !== 200) {
        return {
          code: ErrorCode.INTERNAL_SERVER_ERROR,
          message: res.statusCode === 413 ? '头像不能超过 2MB' : '头像上传失败，请稍后重试',
        }
      }
      const body = JSON.parse(res.data) as ApiResponse<{ avatar_url: string }>
      if (!body || typeof body.code !== 'number'
        || (body.code === 0 && !body.data?.avatar_url)) {
        return { code: ErrorCode.INTERNAL_SERVER_ERROR, message: '头像上传返回格式异常' }
      }
      dispatchUnauthCleanup(body.code)
      return body
    } catch (_) {
      return { code: ErrorCode.INTERNAL_SERVER_ERROR, message: '头像上传失败，请检查网络后重试' }
    }
  },

  async listQuizzes(page = 1, page_size = 20): Promise<ApiResponse<QuizHistoryListResponse>> {
    const qs = `?page=${page}&page_size=${page_size}`
    return request<QuizHistoryListResponse>(`/user/quizzes${qs}`, undefined, 'GET')
  },

  async getQuizDetail(quiz_id: string): Promise<ApiResponse<QuizDetailResponse>> {
    return request<QuizDetailResponse>(`/user/quizzes/${quiz_id}`, undefined, 'GET')
  },
}
