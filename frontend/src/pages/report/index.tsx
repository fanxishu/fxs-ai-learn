import React, { useEffect, useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'
import {
  AppButton,
  Chip,
  NoteCard,
  ProgressTrack,
  RingProgress,
  StateBadge,
} from '@/components'
import { useQuizStore } from '@/store/quiz'
import { useUserStore } from '@/store/user'
import type {
  AnswerRecord,
  Question,
  QuizGenerateResult,
  ReportGenerateResult,
} from '@/types/quiz'

export default function ReportPage() {
  const quiz = useQuizStore(s => s.quiz)
  const records = useQuizStore(s => s.records)
  const report = useQuizStore(s => s.report)
  const input = useQuizStore(s => s.input)
  const loadQuizSession = useQuizStore(s => s.loadQuizSession)
  const loadReportPayload = useQuizStore(s => s.loadReportPayload)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const setRecords = useQuizStore(s => s.setRecords)
  const setReport = useQuizStore(s => s.setReport)
  const reset = useQuizStore(s => s.reset)

  useEffect(() => {
    const hasReport = !!(report || loadReportPayload() || (quiz && quiz.questions.length > 0) || loadQuizSession()?.quiz)
    if (!useUserStore.getState().isLoggedIn && !hasReport) {
      try { Taro.showToast({ title: '请先登录后再使用本功能', icon: 'none', duration: 1800 }) } catch (_) { /* noop */ }
      try { Taro.redirectTo({ url: '/pages/index/index' }) } catch (_) { /* noop */ }
      return
    }
    const payload = loadReportPayload()
    if (payload) {
      if (!quiz) setQuiz(payload.quiz as QuizGenerateResult)
      if (!records || !records.length) setRecords(payload.answer_records)
      if (!report) setReport(payload.report)
    } else if (!quiz) {
      const s = loadQuizSession()
      if (s?.quiz) setQuiz(s.quiz)
    }
  }, [quiz, report, records, loadQuizSession, loadReportPayload, setQuiz, setRecords, setReport])

  const questions = useMemo<Question[]>(() => (quiz?.questions as Question[]) || [], [quiz])
  const acc = useMemo(() => report?.accuracy ?? (records.length
    ? Math.round((records.filter(r => r.is_correct).length / records.length) * 100)
    : 0), [report, records])
  const correct = useMemo(() => (records as AnswerRecord[]).filter(r => r.is_correct).length, [records])
  const total = questions.length || (records as AnswerRecord[]).length || 1

  const mastery = useMemo(() => {
    const per = new Map<string, { total: number; correct: number }>()
    const qs = questions as Question[]
    qs.forEach((q, i) => {
      const kp = q.knowledge_point || '综合'
      const bucket = per.get(kp) || { total: 0, correct: 0 }
      bucket.total += 1
      const rec = (records as AnswerRecord[]).find(r => (r.question_id === q.question_id || r.question_id === `q-${i}`))
      if (rec?.is_correct) bucket.correct += 1
      per.set(kp, bucket)
    })
    return [...per.entries()].map(([kp, v]) => ({
      kp,
      total: v.total,
      correct: v.correct,
      acc: v.total ? Math.round((v.correct / v.total) * 100) : 0,
    }))
  }, [questions, records])

  const accClass =
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low

  const playAgain = () => {
    if (!quiz || !questions.length) {
      reset()
      Taro.switchTab({ url: '/pages/index/index' })
      return
    }
    setRecords([])
    setReport(null)
    Taro.redirectTo({ url: '/pages/quiz/index' })
  }

  const goHome = () => {
    reset()
    Taro.switchTab({ url: '/pages/index/index' })
  }

  const share = () => {
    Taro.showToast({ title: '生成分享海报功能即将上线', icon: 'none', duration: 2000 })
  }

  if (!report) {
    return (
      <View className={styles.page}>
        <View style={{ marginTop: 120, alignItems: 'center', justifyContent: 'center', flex: 1, padding: 48, borderRadius: 24, background: '#fff', boxShadow: '0 2rpx 12rpx rgba(0,0,0,.08)' }}>
          <Text style={{ fontSize: 80, marginBottom: 24 }}>📝</Text>
          <Text style={{ color: '#4E5969', marginBottom: 24 }}>暂无报告，请先完成一次闯关。</Text>
          <AppButton size='lg' variant='primary' onClick={goHome}>去首页开始</AppButton>
        </View>
      </View>
    )
  }

  return (
    <View className={styles.page}>
      <View className={styles.header}>
        <View className={styles.left}>
          <Text className={styles.label}>🎉 闯关完成</Text>
          <Text className={styles.title}>{quiz?.title || `${input?.slice(0, 12) || 'AI'} 闯关报告`}</Text>
          <Text className={styles.sub}>{report.three_line_summary?.[0] || '你的学习成果已经生成！'}</Text>
        </View>
        <RingProgress accuracy={acc} size={150} strokeWidth={12} />
      </View>

      <View className={styles.stats}>
        <View className={styles.item}>
          <Text className={classnames(styles.num, accClass)}>{acc}%</Text>
          <Text className={styles.label}>正确率</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num} style={{ color: '#4e9fff' }}>{correct}/{total}</Text>
          <Text className={styles.label}>答对题数</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num} style={{ color: '#df5f1f' }}>
            +{Math.max(0, correct) * 10}
          </Text>
          <Text className={styles.label}>XP 经验值</Text>
        </View>
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>知识点掌握度</View>
        <View className={styles.right}>共 {mastery.length} 个知识点</View>
      </View>

      <View className='cardsStack' style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {!mastery.length ? (
          <NoteCard variant='advice' title='暂无知识点拆解'>
            本次题目暂未标注知识点标签，建议下次尝试更结构化的知识点输入。
          </NoteCard>
        ) : (
          mastery.map(m => (
            <View key={m.kp} style={{ padding: 24, background: '#fff', borderRadius: 16, boxShadow: '0 2rpx 12rpx rgba(0,0,0,.08)' }}>
              <View style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, gap: 12 }}>
                <View style={{ fontWeight: 600, color: '#1D2129', flex: 1 }}>{m.kp}</View>
                <StateBadge kind={m.acc >= 80 ? 'good' : m.acc >= 60 ? 'info' : 'bad'}>
                  {m.acc}%
                </StateBadge>
              </View>
              <ProgressTrack percent={m.acc} height={10} color={m.acc >= 80 ? 'green' : m.acc >= 60 ? 'blue' : 'red'} />
              <View style={{ marginTop: 8, fontSize: 12, color: '#86909C' }}>答对 {m.correct} / {m.total}</View>
            </View>
          ))
        )}
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>掌握与薄弱点</View>
      </View>
      <View className={styles.cardsStack}>
        <NoteCard variant='mastery-good' title='✅ 已掌握' list={report.mastered_points} listItemClass='good' emptyText='暂无掌握点，再接再厉' />
        <NoteCard variant='mastery-weak' title='⚠️ 待加强' list={report.weak_points} listItemClass='weak' emptyText='表现不错，暂无明显薄弱点' />
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>AI 复盘总结</View>
      </View>
      <View className={styles.cardsStack}>
        {(report.three_line_summary || []).map((line: string, i: number) => (
          <NoteCard key={i} variant='summary' index={i + 1} title={`要点 ${i + 1}`}>
            {line}
          </NoteCard>
        ))}
        <NoteCard variant='advice' title='💡 学习建议'>{report.advice}</NoteCard>
        <NoteCard variant='quote' title='分享金句'>{(report as ReportGenerateResult).share_quote}</NoteCard>
      </View>

      <View style={{ height: 20 }} />

      <View className={styles.bottomBar}>
        <AppButton
          className={styles.btnSecondary}
          size='xl'
          variant='secondary'
          onClick={goHome}
        >
          回首页
        </AppButton>
        <AppButton
          className={styles.btnShare}
          size='xl'
          variant='ghost'
          onClick={share}
        >
          生成分享海报
        </AppButton>
        <AppButton
          className={styles.btnPrimary}
          size='xl'
          variant='primary'
          onClick={playAgain}
        >
          🎯 再闯一次
        </AppButton>
      </View>
    </View>
  )
}
