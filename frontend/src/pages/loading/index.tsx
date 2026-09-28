import React, { useEffect, useMemo, useRef, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'
import { AppButton } from '@/components'
import { useQuizStore } from '@/store/quiz'
import { useUserStore } from '@/store/user'
import { API, toastError } from '@/services/api'
import { DEFAULT_QUESTION_COUNT } from '@/types/quiz'

interface Step {
  key: string
  title: string
  desc: string
}

const STEPS: Step[] = [
  { key: 'analyse', title: '分析输入内容结构', desc: '识别关键知识点与概念边界' },
  { key: 'augment', title: '联网检索参考资料', desc: '关键词搜索或网页提取，增强出题准确性' },
  { key: 'generate', title: '生成 5 道闯关题', desc: '混合单选 / 多选 / 判断，附解析' },
  { key: 'review', title: '校验题目格式', desc: '去重、检查答案与解析匹配' },
  { key: 'finish', title: '准备进入闯关', desc: '即将为你开启答题页面' },
]

export default function LoadingPage() {
  const input = useQuizStore(s => s.input)
  const quiz = useQuizStore(s => s.quiz)
  const loadQuizSession = useQuizStore(s => s.loadQuizSession)
  const saveQuizSession = useQuizStore(s => s.saveQuizSession)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const setRecords = useQuizStore(s => s.setRecords)
  const setReport = useQuizStore(s => s.setReport)

  const [activeIndex, setActiveIndex] = useState(0)
  const [running, setRunning] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const timed = useRef(false)

  const useExisting = useMemo(() => !!quiz && quiz.questions.length > 0, [quiz])

  useEffect(() => {
    if (!useUserStore.getState().isLoggedIn && !useExisting) {
      try { Taro.showToast({ title: '请先登录后再使用本功能', icon: 'none', duration: 1800 }) } catch (_) { /* noop */ }
      try { Taro.redirectTo({ url: '/pages/index/index' }) } catch (_) { /* noop */ }
      return
    }
    if (!input && !useExisting) {
      console.warn('[Loading] 无 input 也无 quiz，回首页')
      Taro.redirectTo({ url: '/pages/index/index' })
      return
    }
    if (useExisting) {
      console.info('[Loading] 已有 quiz 直接进入 quiz 页')
      const t = setTimeout(() => Taro.redirectTo({ url: '/pages/quiz/index' }), 800)
      return () => clearTimeout(t)
    }
    setErrorMsg('')
    setRunning(true)
    setActiveIndex(0)
    let idx = 0
    const iv = setInterval(() => {
      idx = Math.min(idx + 1, STEPS.length - 1)
      setActiveIndex(idx)
    }, 650)
    const run = async () => {
      const userState = useUserStore.getState()
      if (!userState.isLoggedIn) {
        const ok = await userState.wxLoginFlow()
        if (!ok) {
          throw new Error('微信登录失败，请稍后重试')
        }
      }
      try {
        const res = await API.generateQuiz({
          user_input: input,
          question_count: DEFAULT_QUESTION_COUNT,
        })
        if (res.code !== 0 || !res.data) {
          throw new Error(res.message || 'AI 出题失败')
        }
        setQuiz(res.data)
        setRecords([])
        setReport(null)
        saveQuizSession({ quiz: res.data })
        console.log('[Loading] generated:', res.data.quiz_id, 'questions:', res.data.questions.length)
        setActiveIndex(STEPS.length - 1)
        timed.current = true
        setTimeout(() => Taro.redirectTo({ url: '/pages/quiz/index' }), 450)
      } catch (err) {
        console.error('[Loading] generate error:', err)
        setErrorMsg((err as Error).message || '出题失败，请稍后重试')
        setRunning(false)
      } finally {
        clearInterval(iv)
      }
    }
    run()
    return () => clearInterval(iv)
  }, [input, useExisting, loadQuizSession, saveQuizSession, setQuiz, setRecords, setReport])

  const retry = async () => {
    if (!input) {
      toastError('请先在首页输入学习内容')
      Taro.redirectTo({ url: '/pages/index/index' })
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
    setErrorMsg('')
    setRunning(true)
    setActiveIndex(0)
    let idx = 0
    const iv = setInterval(() => {
      idx = Math.min(idx + 1, STEPS.length - 1)
      setActiveIndex(idx)
    }, 650)
    try {
      const res = await API.generateQuiz({
        user_input: input,
        question_count: DEFAULT_QUESTION_COUNT,
      })
      if (res.code !== 0 || !res.data) throw new Error(res.message || 'AI 出题失败')
      setQuiz(res.data)
      setRecords([])
      setReport(null)
      saveQuizSession({ quiz: res.data })
      setTimeout(() => Taro.redirectTo({ url: '/pages/quiz/index' }), 450)
    } catch (err) {
      console.error('[Loading] retry error:', err)
      setErrorMsg((err as Error).message || '重试失败')
      setRunning(false)
    } finally {
      clearInterval(iv)
    }
  }

  return (
    <View className={styles.page}>
      <View className={styles.hero}>
        <Text className={styles.emoji}>🧠</Text>
        <Text className={styles.title}>{useExisting ? '准备进入闯关' : 'AI 正在为你出题'}</Text>
        <Text className={styles.sub}>
          {useExisting
            ? '检测到未完成的闯关记录，正在恢复你的答题进度...'
            : '正在创建出题任务并轮询结果，通常需要十几秒。请稍候，不要离开本页。'}
        </Text>
      </View>

      <View className={styles.box}>
        <View className={styles.inputPreview}>
          📝 你的输入：{input || '(未提供，使用上次缓存的题目)'}
        </View>

        <View className={styles.steps}>
          {STEPS.map((s, i) => {
            const cls =
              errorMsg && i === activeIndex
                ? styles.pending
                : i < activeIndex
                  ? styles.done
                  : i === activeIndex
                    ? styles.running
                    : styles.pending
            return (
              <View key={s.key} className={classnames(styles.step, cls)}>
                <View className={styles.bullet}>
                  {i < activeIndex ? '✓' : i + 1}
                </View>
                <View className={styles.content}>
                  <Text className={styles.title}>{s.title}</Text>
                  <Text className={styles.desc}>{s.desc}</Text>
                </View>
              </View>
            )
          })}
        </View>
      </View>

      {!!errorMsg && (
        <View className={styles.errorBox}>
          <Text>😵 出题出现问题：{errorMsg}</Text>
          <View className={styles.actions}>
            <AppButton size='md' variant='ghost' onClick={() => Taro.redirectTo({ url: '/pages/index/index' })}>
              返回首页
            </AppButton>
            <AppButton size='md' variant='primary' onClick={retry} disabled={running}>
              {running ? '正在重试...' : '🔄 再试一次'}
            </AppButton>
          </View>
        </View>
      )}
    </View>
  )
}
