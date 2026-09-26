import Taro from '@tarojs/taro'
import type {
  ApiResponse,
  QuizGenerateRequest,
  QuizGenerateResult,
  ReportGenerateRequest,
  ReportGenerateResult,
} from '@/types/quiz'
import { mockQuiz, mockReport } from '@/data/quizMock'
import { ErrorCode, ERROR_TOAST } from '@/types/common'

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
  method: 'GET' | 'POST' = 'POST',
): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${API_PREFIX}${path}`
  console.log(`[API] ${method} ${url}`, data)

  try {
    const res = await Taro.request<ApiResponse<T>>({
      url,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      timeout: 30000,
    })
    const body = res.data ?? ({} as ApiResponse<T>)
    // 兼容后端可能不返回 code 的场景
    if (typeof body.code !== 'number') {
      body.code = ErrorCode.INTERNAL_SERVER_ERROR
      body.message = body.message || '服务返回格式异常'
    }
    console.log(`[API] ${url} -> code=${body.code} msg=${body.message}`)
    return body
  } catch (err: unknown) {
    console.error(`[API] ${url} 网络异常:`, err)
    const msg = err instanceof Error ? err.message : 'Network Error'
    // Task10 分支：Network Error 统一错误码
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
    // 用户文案 Toast（仅一次）
    const toast = codeToToast(res.code, res.message || '生成失败，请重试')
    if (toast) toastError(toast)
    // 兜底 mock
    console.warn('[API] generateQuiz 失败（code=' + res.code + '），使用 mock 数据')
    return { code: 0, message: 'ok', data: mockQuiz(payload) }
  },

  async generateReport(
    payload: ReportGenerateRequest,
  ): Promise<ApiResponse<ReportGenerateResult>> {
    const res = await request<ReportGenerateResult>('/report/generate', payload)
    if (res.code === 0 && res.data) return res
    const toast = codeToToast(res.code, res.message || '生成报告失败，请重试')
    if (toast) toastError(toast)
    console.warn('[API] generateReport 失败（code=' + res.code + '），使用 mock 数据')
    return { code: 0, message: 'ok', data: mockReport(payload) }
  },
}
