import Taro from '@tarojs/taro'
import type {
  ApiResponse,
  QuizGenerateRequest,
  QuizGenerateResult,
  ReportGenerateRequest,
  ReportGenerateResult,
} from '@/types/quiz'
import { mockQuiz, mockReport } from '@/data/quizMock'

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

export async function request<T = unknown> (
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
    console.log(`[API] ${url} -> code=${body.code} msg=${body.message}`)
    return body
  } catch (err) {
    console.error(`[API] ${url} 网络异常:`, err)
    return {
      code: 5000,
      message: '网络请求失败，已使用本地兜底数据',
    } as ApiResponse<T>
  }
}

export function toastError (msg: string) {
  Taro.showToast({ title: msg, icon: 'none', duration: 2000 })
}

export const API = {
  async generateQuiz (payload: QuizGenerateRequest): Promise<ApiResponse<QuizGenerateResult>> {
    const res = await request<QuizGenerateResult>('/quiz/generate', payload)
    if (res.code === 0 && res.data) return res
    // 兜底 mock
    console.warn('[API] generateQuiz 失败，使用 mock 数据')
    return { code: 0, message: 'ok', data: mockQuiz(payload) }
  },

  async generateReport (
    payload: ReportGenerateRequest,
  ): Promise<ApiResponse<ReportGenerateResult>> {
    const res = await request<ReportGenerateResult>('/report/generate', payload)
    if (res.code === 0 && res.data) return res
    console.warn('[API] generateReport 失败，使用 mock 数据')
    return { code: 0, message: 'ok', data: mockReport(payload) }
  },
}
