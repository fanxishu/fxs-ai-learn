import React, { useEffect, useMemo, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import styles from './index.module.scss'
import {
  AppButton,
  Chip,
  CoinBadge,
  ExplainBox,
  ProgressTrack,
  QuizOption,
  StateBadge,
} from '@/components'
import { useQuizStore } from '@/store/quiz'
import { useUserStore } from '@/store/user'
import type {
  AnswerRecord,
  Question,
  QuestionOption as QOpt,
  QuizGenerateResult,
  ReportGenerateResult,
} from '@/types/quiz'
import { API, toastError } from '@/services/api'

type Selected = string | string[]

const isAnswerEqual = (u: Selected, a: string | string[]): boolean => {
  if (Array.isArray(a)) {
    if (!Array.isArray(u)) return false
    const A = [...a].sort()
    const B = [...u].sort()
    return A.length === B.length && A.every((x, i) => x === B[i])
  }
  return u === a
}

const typeColorMap = {
  single: 'blue',
  multiple: 'purple',
  judge: 'green',
} as const

const typeLabelMap = {
  single: '单选题',
  multiple: '多选题',
  judge: '判断题',
} as const

export default function QuizPage() {
  const quiz = useQuizStore(s => s.quiz)
  const loadQuizSession = useQuizStore(s => s.loadQuizSession)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const setRecords = useQuizStore(s => s.setRecords)
  const records = useQuizStore(s => s.records)
  const setReport = useQuizStore(s => s.setReport)
  const saveReportPayload = useQuizStore(s => s.saveReportPayload)
  const pushHistory = useQuizStore(s => s.pushHistory)
  const input = useQuizStore(s => s.input)

  const [cursor, setCursor] = useState(0)
  const [selected, setSelected] = useState<Selected | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [reward, setReward] = useState<null | { coin: number; xp: number }>(null)
  const [correctCount, setCorrectCount] = useState(0)
  const [loadingReport, setLoadingReport] = useState(false)

  useEffect(() => {
    const hasQuiz = !!(quiz && quiz.questions.length > 0) || !!loadQuizSession()?.quiz
    if (!useUserStore.getState().isLoggedIn && !hasQuiz) {
      try { Taro.showToast({ title: '请先登录后再使用本功能', icon: 'none', duration: 1800 }) } catch (_) { /* noop */ }
      try { Taro.redirectTo({ url: '/pages/index/index' }) } catch (_) { /* noop */ }
      return
    }
    const boot = () => {
      if (quiz && quiz.questions.length > 0) return
      const sess = loadQuizSession()
      if (sess?.quiz) setQuiz(sess.quiz)
    }
    boot()
  }, [quiz, loadQuizSession, setQuiz])

  const questions = useMemo<Question[]>(() => {
    const qs = quiz?.questions || []
    return qs.map((q, i) => ({
      ...q,
      question_id: q.question_id || q.id || `q-${i}`,
    }))
  }, [quiz])

  const current: Question | undefined = questions[cursor]

  const isMultiple = current?.question_type === 'multiple'
  const typeColor = current ? (typeColorMap[current.question_type] as any) : 'blue'

  const canConfirm = useMemo(() => {
    if (!current) return false
    if (Array.isArray(selected)) return selected.length > 0
    return !!selected
  }, [current, selected])

  const toggleOption = (opt: QOpt) => {
    if (submitted) return
    if (!current) return
    if (isMultiple) {
      setSelected(prev => {
        const arr = Array.isArray(prev) ? [...prev] : []
        const i = arr.indexOf(opt.key)
        if (i >= 0) arr.splice(i, 1)
        else arr.push(opt.key)
        return arr
      })
    } else {
      setSelected(opt.key)
    }
  }

  const optionState = (opt: QOpt): any => {
    if (!current) return 'normal'
    const key = opt.key
    const selContains = Array.isArray(selected)
      ? selected.includes(key)
      : selected === key
    const answer = Array.isArray(current.answer) ? current.answer : [current.answer]
    const ansContains = answer.includes(key)
    if (!submitted) return selContains ? 'selected' : 'normal'
    if (ansContains) return 'correct'
    if (selContains && !ansContains) return 'wrong'
    return 'normal'
  }

  const onConfirm = () => {
    if (!current) return
    if (submitted) return
    if (!canConfirm) {
      Taro.showToast({ title: isMultiple ? '请至少选一个选项' : '请选择一个选项', icon: 'none' })
      return
    }
    const isCorrect = isAnswerEqual(selected as Selected, current.answer)
    const rec: AnswerRecord = {
      question_id: current.question_id || `q-${cursor}`,
      user_answer: selected as string | string[],
      is_correct: isCorrect,
      time_spent_ms: 0,
    }
    const nextRecords = [...(records || []).filter(x => x.question_id !== rec.question_id), rec]
    setRecords(nextRecords)
    setSubmitted(true)
    if (isCorrect) {
      const coin = 5
      const xp = 10
      setCorrectCount(c => c + 1)
      setReward({ coin, xp })
      setTimeout(() => setReward(null), 1600)
      Taro.vibrateShort?.({ type: 'light' })
    } else {
      setReward(null)
      Taro.vibrateShort?.({ type: 'medium' })
    }
  }

  const goPrev = () => {
    if (!current) return
    if (cursor > 0) {
      const prev = questions[cursor - 1]
      const prevRec = (records || []).find(r => r.question_id === (prev.question_id || `q-${cursor - 1}`))
      setCursor(c => c - 1)
      if (prevRec) {
        setSelected(prevRec.user_answer as Selected)
        setSubmitted(true)
      } else {
        setSelected(null)
        setSubmitted(false)
      }
      setReward(null)
    }
  }

  const goNext = () => {
    if (!current) return
    if (!submitted) return
    if (cursor < questions.length - 1) {
      setCursor(c => c + 1)
      setSelected(null)
      setSubmitted(false)
      setReward(null)
    } else {
      finishQuiz()
    }
  }

  const finishQuiz = async () => {
    const userState = useUserStore.getState()
    if (!userState.isLoggedIn) {
      const ok = await userState.wxLoginFlow()
      if (!ok) {
        toastError('微信登录失败，请稍后重试')
        return
      }
    }
    setLoadingReport(true)
    try {
      const finalRecords = (records || []).slice()
      const correctNow = finalRecords.filter(r => r.is_correct).length
      const total = questions.length
      console.log(`[Quiz] 完成 ${correctNow}/${total}，生成报告...`)
      const quizIdRaw = ((quiz as QuizGenerateResult)?.quiz_id || `quiz-gen-${Date.now()}`).toString().trim() || `quiz-gen-${Date.now()}`
      const quizObj = (quiz as QuizGenerateResult) && (quiz as QuizGenerateResult).questions ? (quiz as QuizGenerateResult) : { questions }
      const payload = {
        quiz_id: quizIdRaw,
        quiz: quizObj,
        answer_records: finalRecords,
      }
      console.log('[Quiz] finishQuiz payload →', { quiz_id: payload.quiz_id, quiz_keys: Object.keys(payload.quiz || {}), qCount: (payload.quiz as any)?.questions?.length, recCount: finalRecords.length, firstRec: finalRecords[0] })
      const res = await API.generateReport(payload)
      if (res.code !== 0 || !res.data) {
        throw new Error(res.message || '报告生成失败')
      }
      const report: ReportGenerateResult = res.data
      setReport(report)
      saveReportPayload({
        quiz: quizObj,
        answer_records: finalRecords,
        report,
      })
      const accuracy = report.accuracy
      pushHistory({
        id: `h-${Date.now()}`,
        title: quiz?.title || `${input?.slice(0, 12) || 'AI'} 闯关报告`,
        user_input: input || '',
        created_at: Date.now(),
        accuracy,
        total,
        correct: correctNow,
        share_quote: report.share_quote,
        mastered_points: report.mastered_points,
        weak_points: report.weak_points,
        quiz_snapshot: {
          quiz: quizObj,
          answer_records: finalRecords,
          report,
        },
      })
      Taro.redirectTo({ url: '/pages/report/index' })
    } catch (err) {
      console.error('[Quiz] finishQuiz error:', err)
      toastError((err as Error).message || '生成报告失败，请重试')
    } finally {
      setLoadingReport(false)
    }
  }

  const progress = useMemo(() => {
    if (!questions.length) return 0
    const base = Math.round((cursor / questions.length) * 100)
    if (submitted) return Math.round(((cursor + 1) / questions.length) * 100)
    return base
  }, [cursor, questions.length, submitted])

  if (!current) {
    return (
      <View className={styles.page}>
        <View className={styles.card} style={{ marginTop: 120, alignItems: 'center' }}>
          <Text style={{ fontSize: 48, marginBottom: 16 }}>⏳</Text>
          <Text style={{ color: '#4E5969' }}>没有可答题的闯关，请返回首页重新生成。</Text>
          <View style={{ marginTop: 24 }}>
            <AppButton size='lg' variant='primary' onClick={() => Taro.redirectTo({ url: '/pages/index/index' })}>
              返回首页
            </AppButton>
          </View>
        </View>
      </View>
    )
  }

  return (
    <View className={styles.page}>
      <View className={styles.header}>
        <View className={styles.topRow}>
          <Text className={styles.title}>{quiz?.title || '闯关答题'}</Text>
          <CoinBadge variant='soft'>
            答对 {correctCount}/{questions.length}
          </CoinBadge>
        </View>
        <View className={styles.progress}>
          <ProgressTrack
            percent={progress}
            height={12}
            color='blue'
          />
          <View className={styles.meta}>
            <Text>第 {cursor + 1} / {questions.length} 题</Text>
            <Text>进度 {progress}%</Text>
          </View>
        </View>
      </View>

      <View className={styles.card}>
        <View className={styles.typeRow}>
          <Chip color={typeColor} size='sm'>{typeLabelMap[current.question_type]}</Chip>
          {current.knowledge_point && <Chip color='soft-orange' size='sm'>📌 {current.knowledge_point}</Chip>}
          {submitted && (
            <StateBadge kind={isAnswerEqual(selected as Selected, current.answer) ? 'good' : 'bad'}>
              {isAnswerEqual(selected as Selected, current.answer) ? '回答正确' : '回答错误'}
            </StateBadge>
          )}
        </View>

        <Text className={styles.stem}>{current.stem}</Text>

        <View className={styles.options}>
          {current.options.map(opt => (
            <QuizOption
              key={opt.key}
              keyLabel={opt.key}
              text={opt.text}
              state={optionState(opt)}
              disabled={submitted}
              onClick={() => toggleOption(opt)}
            />
          ))}
        </View>

        {reward && (
          <View className={styles.rewardToast}>
            <Text className={styles.emoji}>🎉</Text>
            <Text className={styles.text}>+{reward.coin} 金币 · +{reward.xp} XP</Text>
          </View>
        )}

        {submitted && (
          <ExplainBox
            state={isAnswerEqual(selected as Selected, current.answer) ? 'good' : 'bad'}
            title={isAnswerEqual(selected as Selected, current.answer) ? '讲解' : '正确答案与讲解'}
            text={
              (Array.isArray(current.answer) ? current.answer.join('、') : current.answer) +
              (current.explanation ? `｜${current.explanation}` : '')
            }
          />
        )}
      </View>

      <View className={styles.bottomBar}>
        <View className={styles.statRow}>
          <Text>已提交 {records.length} 题</Text>
          <Text>正确 {records.filter(r => r.is_correct).length} / {records.length}</Text>
        </View>
        <View className={`${styles.navRow} ${cursor <= 0 ? styles.navRowSingle : ''}`}>
          {cursor > 0 && (
            <AppButton
              size='xl'
              variant='secondary'
              onClick={goPrev}
            >
              ⬅ 上一题
            </AppButton>
          )}
          {!submitted ? (
            <AppButton
              className={`${styles.btnConfirmPrimary} ${cursor <= 0 ? styles.btnFull : ''}`}
              block
              size='xl'
              variant='primary'
              disabled={!canConfirm}
              onClick={onConfirm}
            >
              判定本答
            </AppButton>
          ) : (
            <AppButton
              className={`${styles.btnConfirmPrimary} ${cursor <= 0 ? styles.btnFull : ''}`}
              block
              size='xl'
              variant='primary'
              loading={loadingReport && cursor === questions.length - 1}
              onClick={goNext}
            >
              {cursor < questions.length - 1 ? '下一题 →' : loadingReport ? 'AI 生成报告中...' : '查看报告 🏆'}
            </AppButton>
          )}
        </View>
      </View>
    </View>
  )
}
