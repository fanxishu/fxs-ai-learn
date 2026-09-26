import React, { useCallback, useEffect, useMemo } from 'react'
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
import { API, toastError } from '@/services/api'
import { validateAndToast } from '@/services/contentFilter'
import type { HistoryItem } from '@/types/quiz'
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

  const [loading, setLoading] = React.useState(false)

  useDidShow(() => {
    loadHistory()
  })

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const recent = useMemo<HistoryItem[]>(() => (history || []).slice(0, 3), [history])

  const canSubmit = input.trim().length >= INPUT_MIN_LEN && input.trim().length <= INPUT_MAX_LEN

  const handleExample = (text: string) => {
    setInput(text)
  }

  const accuracyClass = (acc: number) =>
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low

  const openHistoryItem = (item: HistoryItem) => {
    if (!item.quiz_snapshot) return
    reset()
    setQuiz(item.quiz_snapshot.quiz)
    saveQuizSession({ quiz: item.quiz_snapshot.quiz })
    const snap = item.quiz_snapshot
    useQuizStore.getState().setRecords(snap.answer_records)
    useQuizStore.getState().setReport(snap.report)
    Taro.navigateTo({ url: '/pages/report/index' })
  }

  const onSubmit = useCallback(async () => {
    // Task7 第一层：前端 contentFilter 快速拦截
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
        <CoinBadge variant='pill'>AI 出题 · 立即闯关</CoinBadge>
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
                <StateBadge kind={item.accuracy >= 60 ? 'good' : 'bad'}>
                  正确率 {item.accuracy}%
                </StateBadge>
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
