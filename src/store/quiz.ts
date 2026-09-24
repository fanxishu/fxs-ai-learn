import { create } from 'zustand'
import Taro from '@tarojs/taro'
import type {
  Question,
  AnswerRecord,
  QuizGenerateResult,
  ReportGenerateResult,
  HistoryItem,
} from '@/types/quiz'

export interface QuizStoreState {
  input: string
  quiz: QuizGenerateResult | null
  questions: Question[]
  records: AnswerRecord[]
  report: ReportGenerateResult | null
  history: HistoryItem[]

  setInput: (v: string) => void
  setQuiz: (q: QuizGenerateResult | null) => void
  setQuestions: (qs: Question[]) => void
  setRecords: (r: AnswerRecord[]) => void
  setReport: (r: ReportGenerateResult | null) => void
  reset: () => void

  saveQuizSession: (session: {
    quiz: QuizGenerateResult
  }) => void
  loadQuizSession: () => { quiz: QuizGenerateResult } | null
  saveReportPayload: (payload: {
    quiz: { questions: Question[] }
    answer_records: AnswerRecord[]
    report: ReportGenerateResult
  }) => void
  loadReportPayload: () => ({
    quiz: { questions: Question[] }
    answer_records: AnswerRecord[]
    report: ReportGenerateResult
  }) | null

  pushHistory: (item: HistoryItem) => void
  loadHistory: () => HistoryItem[]
  clearHistory: () => void
  removeHistoryItem: (id: string) => void
}

const STORAGE_QUIZ = 'quiz_session'
const STORAGE_REPORT = 'report_payload'
const STORAGE_HISTORY = 'quiz_history_list'

const MAX_HISTORY = 50

export const useQuizStore = create<QuizStoreState>((set, get) => ({
  input: '',
  quiz: null,
  questions: [],
  records: [],
  report: null,
  history: [],

  setInput: (v) => set({ input: v }),
  setQuiz: (q) => set({ quiz: q, questions: q?.questions ?? [] }),
  setQuestions: (qs) => set({ questions: qs }),
  setRecords: (r) => set({ records: r }),
  setReport: (r) => set({ report: r }),
  reset: () => set({ input: '', quiz: null, questions: [], records: [], report: null }),

  saveQuizSession: (session) => {
    try {
      Taro.setStorageSync(STORAGE_QUIZ, JSON.stringify(session))
    } catch (err) {
      console.error('[QuizStore] saveQuizSession error:', err)
    }
  },
  loadQuizSession: () => {
    try {
      const raw = Taro.getStorageSync(STORAGE_QUIZ)
      return raw ? JSON.parse(raw) : null
    } catch (err) {
      console.error('[QuizStore] loadQuizSession error:', err)
      return null
    }
  },
  saveReportPayload: (payload) => {
    try {
      Taro.setStorageSync(STORAGE_REPORT, JSON.stringify(payload))
    } catch (err) {
      console.error('[QuizStore] saveReportPayload error:', err)
    }
  },
  loadReportPayload: () => {
    try {
      const raw = Taro.getStorageSync(STORAGE_REPORT)
      return raw ? JSON.parse(raw) : null
    } catch (err) {
      console.error('[QuizStore] loadReportPayload error:', err)
      return null
    }
  },

  pushHistory: (item) => {
    const list = [item, ...(get().history || get().loadHistory())].slice(0, MAX_HISTORY)
    set({ history: list })
    try {
      Taro.setStorageSync(STORAGE_HISTORY, JSON.stringify(list))
    } catch (err) {
      console.error('[QuizStore] pushHistory write error:', err)
    }
  },
  loadHistory: () => {
    try {
      const raw = Taro.getStorageSync(STORAGE_HISTORY)
      const list: HistoryItem[] = raw ? JSON.parse(raw) : []
      set({ history: list })
      return list
    } catch (err) {
      console.error('[QuizStore] loadHistory error:', err)
      return []
    }
  },
  clearHistory: () => {
    set({ history: [] })
    try {
      Taro.removeStorageSync(STORAGE_HISTORY)
    } catch (err) {
      console.error('[QuizStore] clearHistory error:', err)
    }
  },
  removeHistoryItem: (id) => {
    const list = get().history.filter(x => x.id !== id)
    set({ history: list })
    try {
      Taro.setStorageSync(STORAGE_HISTORY, JSON.stringify(list))
    } catch (err) {
      console.error('[QuizStore] removeHistoryItem error:', err)
    }
  },
}))

