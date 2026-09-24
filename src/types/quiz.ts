// ============================================
// 鱼皮 AI 闯关 - 业务类型定义
// ============================================

export type QuestionType = 'single' | 'multiple' | 'judge'

export interface QuestionOption {
  key: string
  text: string
}

export interface Question {
  id?: string
  question_id?: string
  question_type: QuestionType
  stem: string
  options: QuestionOption[]
  answer: string | string[]
  knowledge_point?: string
  explanation?: string
  difficulty?: number
}

export interface AnswerRecord {
  question_id: string
  user_answer: string | string[]
  is_correct: boolean
  time_spent_ms?: number
}

export interface QuizGenerateRequest {
  user_input: string
  question_count?: number
}

export interface QuizGenerateResult {
  quiz_id: string
  title?: string
  questions: Question[]
}

export interface ScoreSummary {
  accuracy: number
  total_questions: number
  correct_count: number
  wrong_count: number
  per_knowledge: { knowledge_point: string; accuracy: number; total: number; correct: number }[]
}

export interface ReportGenerateRequest {
  quiz_id?: string
  quiz: { questions: Question[] } | Question[]
  answer_records: AnswerRecord[]
}

export interface ReportGenerateResult {
  accuracy: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: [string, string, string] | string[]
  advice: string
  share_quote: string
  score_summary?: ScoreSummary
}

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data?: T
}

export interface HistoryItem {
  id: string
  title: string
  user_input: string
  created_at: number
  accuracy: number
  total: number
  correct: number
  share_quote?: string
  mastered_points?: string[]
  weak_points?: string[]
  quiz_snapshot?: {
    quiz: QuizGenerateResult
    answer_records: AnswerRecord[]
    report: ReportGenerateResult
  }
}

export const INPUT_MIN_LEN = 5
export const INPUT_MAX_LEN = 500
export const DEFAULT_QUESTION_COUNT = 5

