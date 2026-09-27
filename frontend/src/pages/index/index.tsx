import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'
import {
  AppButton,
  AppInput,
  Chip,
  CoinBadge,
  StateBadge,
} from '@/components'
import { useQuizStore } from '@/store/quiz'
import { useUserStore } from '@/store/user'
import { API, toastError } from '@/services/api'
import { validateAndToast } from '@/services/contentFilter'
import type { HistoryItem, Question } from '@/types/quiz'
import type { QuizHistoryItem as UserQuizHistoryItem } from '@/types/user'
import {
  DEFAULT_QUESTION_COUNT,
  INPUT_MAX_LEN,
  INPUT_MIN_LEN,
} from '@/types/quiz'

// Task8: 首页 6 个推荐 Chip（Task8 要求）
const EXAMPLES = [
  'Java 设计模式',
  'RAG 检索增强生成',
  'HTTP 与 HTTPS 区别',
  'React Hooks 核心用法',
  'Python 列表推导式',
  'JavaScript 闭包',
]

export default function HomePage() {
  const input = useQuizStore(s => s.input)
  const setInput = useQuizStore(s => s.setInput)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const saveQuizSession = useQuizStore(s => s.saveQuizSession)
  const reset = useQuizStore(s => s.reset)
  const loadHistory = useQuizStore(s => s.loadHistory)
  const history = useQuizStore(s => s.history)

  const isLoggedIn = useUserStore(s => s.isLoggedIn)
  const user = useUserStore(s => s.user)
  const total_xp = user?.total_xp ?? 0
  const nickname = user?.nickname || '学习者'

  const [loading, setLoading] = React.useState(false)
  const [userRecent, setUserRecent] = useState<UserQuizHistoryItem[] | null>(null)

  useDidShow(async () => {
    loadHistory()
    const wxLoginFlow = useUserStore.getState().wxLoginFlow
    if (!useUserStore.getState().isLoggedIn) await wxLoginFlow()
    if (useUserStore.getState().isLoggedIn) {
      API.listQuizzes(1, 3).then(res => {
        if (res.code === 0 && res.data) setUserRecent(res.data.items || [])
      }).catch(() => { /* fallback to local history */ })
    } else {
      setUserRecent(null)
    }
  })

  useEffect(() => {
    loadHistory()
    const run = async () => {
      const state = useUserStore.getState()
      if (!state.isLoggedIn) await state.wxLoginFlow()
      if (useUserStore.getState().isLoggedIn) {
        const res = await API.listQuizzes(1, 3)
        if (res.code === 0 && res.data) setUserRecent(res.data.items || [])
      }
    }
    run().catch(err => console.warn('[HomePage] mount refresh err:', err))
  }, [loadHistory])

  const recent = useMemo(() => {
    if (userRecent && userRecent.length) {
      return userRecent.map(x => ({
        id: x.quiz_id,
        title: x.title,
        correct: x.correct_count,
        total: x.question_count,
        accuracy: x.accuracy,
        total_xp: x.total_xp,
        created_at: x.created_at,
        _fromUser: true,
      })) as unknown as (HistoryItem & { _fromUser?: boolean; total_xp?: number })[]
    }
    return (history || []).slice(0, 3) as (HistoryItem & { _fromUser?: boolean; total_xp?: number })[]
  }, [userRecent, history])

  const canSubmit = input.trim().length >= INPUT_MIN_LEN && input.trim().length <= INPUT_MAX_LEN

  const handleExample = (text: string) => {
    setInput(text)
  }

  const accuracyClass = (acc: number) =>
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low

  const openHistoryItem = useCallback(async (item: HistoryItem & { _fromUser?: boolean }) => {
    if ((item as any)._fromUser) {
      Taro.showLoading({ title: '加载中...', mask: true })
      try {
        const res = await API.getQuizDetail(item.id)
        if (res.code !== 0 || !res.data) {
          toastError(res.message || '加载失败，请重试')
          return
        }
        const detail = res.data
        const fakeQuiz = {
          quiz_id: detail.quiz_id,
          title: detail.title,
          questions: (detail.questions || []) as Question[],
        }
        setQuiz(fakeQuiz as any)
        saveQuizSession({ quiz: fakeQuiz as any })
        useQuizStore.getState().setRecords((detail.answer_records || []) as any[])
        useQuizStore.getState().setReport((detail.report as any) || null)
        useQuizStore.getState().saveReportPayload({
          quiz: { questions: (detail.questions || []) as Question[] },
          answer_records: (detail.answer_records || []) as any[],
          report: (detail.report as any) || null,
        })
        Taro.navigateTo({ url: '/pages/report/index' })
      } catch (err) {
        console.error('[HomePage] openHistoryItem user err:', err)
        toastError('加载失败，请稍后重试')
      } finally {
        Taro.hideLoading()
      }
      return
    }
    if (!item.quiz_snapshot) return
    reset()
    setQuiz(item.quiz_snapshot.quiz)
    saveQuizSession({ quiz: item.quiz_snapshot.quiz })
    const snap = item.quiz_snapshot
    useQuizStore.getState().setRecords(snap.answer_records)
    useQuizStore.getState().setReport(snap.report)
    Taro.navigateTo({ url: '/pages/report/index' })
  }, [reset, setQuiz, saveQuizSession])

  const onSubmit = useCallback(async () => {
    if (!validateAndToast(input)) return
    const text = input.trim()
    if (text.length < INPUT_MIN_LEN) {
      toastError(`至少输入 ${INPUT_MIN_LEN} 个字`)
      return
    }
    if (text.length > INPUT_MAX_LEN) {
      toastError(`不能超过 ${INPUT_MAX_LEN} 个字`)
      return
    }
    const userState = useUserStore.getState()
    if (!userState.isLoggedIn) {
      const ok = await userState.wxLoginFlow()
      if (!ok) {
        toastError('微信登录失败，请稍后重试')
        return
      }
    }
    setLoading(true)
    try {
      const res = await API.generateQuiz({
        user_input: text,
        question_count: DEFAULT_QUESTION_COUNT,
      })
      if (res.code !== 0 || !res.data) {
        toastError(res.message || '生成失败，请重试')
        return
      }
      reset()
      setInput(text)
      setQuiz(res.data)
      saveQuizSession({ quiz: res.data })
      console.log('[HomePage] generated quiz_id =', res.data.quiz_id, 'questions =', res.data.questions.length)
      Taro.navigateTo({ url: '/pages/loading/index' })
    } catch (err) {
      console.error('[HomePage] generateQuiz error:', err)
      toastError('生成失败，请稍后再试')
    } finally {
      setLoading(false)
    }
  }, [input, reset, setInput, setQuiz, saveQuizSession])

  return (
    <View className={styles.page}>
      <View className={styles.topBar}>
        <View className={styles.brand}>
          <Text>🐟</Text>
          <Text>鱼皮 AI 闯关</Text>
        </View>
        <View className={styles.userBadgeWrap}>
          <Text className={styles.greetText}>Hi, {nickname}</Text>
          <CoinBadge variant='pill'>🔥 XP {total_xp}</CoinBadge>
        </View>
      </View>

      <View className={styles.hero}>
        <Text className={styles.title}>万物皆可闯关，把知识变成游戏</Text>
        <Text className={styles.subtitle}>输入你想学的知识点，AI 自动生成 5 道趣味闯关题，答对有讲解，答错也有深度解析。</Text>
        <View className={styles.badges}>
          {['单选 · 多选 · 判断', '即时反馈', '复盘报告'].map(t => (
            <View key={t} className={styles.hintChip}>{t}</View>
          ))}
        </View>
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>① 输入知识点</View>
        <View className={styles.right}>支持 {INPUT_MIN_LEN}~{INPUT_MAX_LEN} 字</View>
      </View>

      <View className={styles.inputArea}>
        <AppInput
          label='你今天想学点什么？'
          placeholder='例如：Python 列表和字典的区别'
          value={input}
          onChange={setInput}
          min={INPUT_MIN_LEN}
          max={INPUT_MAX_LEN}
          minHeight={260}
          disabled={loading}
        />

        <View className={styles.breadcrumbs}>
          {EXAMPLES.map(ex => (
            <Chip
              key={ex}
              color='soft-blue'
              size='sm'
              onClick={() => handleExample(ex)}
            >
              {ex}
            </Chip>
          ))}
        </View>
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>② 最近闯关</View>
        <View
          className={styles.right}
          onClick={() => Taro.switchTab({ url: '/pages/history/index' })}
        >
          查看全部
        </View>
      </View>

      <View className={styles.recent}>
        {!recent.length ? (
          <View className={styles.empty}>还没有闯关记录，输入一个知识点开始吧 ✨</View>
        ) : (
          recent.map(item => (
            <View key={item.id} className={styles.card} onClick={() => openHistoryItem(item)}>
              <View className={styles.rowTop}>
                <Text className={styles.title}>{item.title}</Text>
                <View className={styles.rightBadges}>
                  {(item as any).total_xp ? (
                    <CoinBadge size='sm' variant='soft'>+XP {(item as any).total_xp}</CoinBadge>
                  ) : null}
                  <StateBadge kind={item.accuracy >= 60 ? 'good' : 'bad'}>
                    正确率 {item.accuracy}%
                  </StateBadge>
                </View>
              </View>
              <View className={styles.sub}>
                <Text className={classnames(styles.score, accuracyClass(item.accuracy))}>
                  {item.correct}/{item.total} 题
                </Text>
                <Text>·</Text>
                <Text>{new Date(item.created_at).toLocaleDateString()}</Text>
              </View>
            </View>
          ))
        )}
      </View>

      <View className={styles.footerActions}>
        <AppButton
          className={styles.primaryButton}
          block
          size='xl'
          variant='primary'
          loading={loading}
          disabled={!canSubmit || loading}
          onClick={onSubmit}
        >
          {loading ? 'AI 正在出题中...' : '🎯 开始闯关'}
        </AppButton>
      </View>
    </View>
  )
}
