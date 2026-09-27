import type { ApiResponse } from './common'
import type { Question, AnswerRecord, ReportGenerateResult } from './quiz'

export interface UserProfile {
  id: number
  nickname: string
  avatar_url: string
  total_xp: number
  created_at?: string
  updated_at?: string
}

export interface ProfileStats {
  quiz_count: number
  correct_count: number
  total_questions: number
  average_accuracy: number
}

export interface UserLoginResponse {
  token: string
  user: UserProfile
}

export interface UserProfileResponse {
  user: UserProfile
  stats: ProfileStats
}

export interface WxLoginRequest {
  code: string
}

export interface UpdateProfileRequest {
  nickname?: string
  avatar_url?: string
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  question_count: number
  correct_count: number
  accuracy: number
  total_xp: number
  created_at: string
}

export interface QuizHistoryListResponse {
  items: QuizHistoryItem[]
  page: number
  page_size: number
  total: number
  has_more: boolean
}

export interface QuizDetailResponse {
  quiz_id: string
  title: string
  created_at: string
  summary?: string
  user_input?: string
  questions: Question[]
  answer_records: AnswerRecord[]
  answer_summary?: {
    total_questions: number
    correct_count: number
    accuracy: number
    total_xp: number
    created_at?: string
  } | null
  accuracy: number
  correct_count: number
  total_questions: number
  total_xp: number
  report: ReportGenerateResult | null
}

export type UserApiResponse<T> = ApiResponse<T>
