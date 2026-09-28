import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { View, Text, Input, Button, Image, Form } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'
import { AppButton, StateBadge } from '@/components'
import { useQuizStore } from '@/store/quiz'
import { useUserStore } from '@/store/user'
import { API, getAvatarUrl, toastError } from '@/services/api'
import { validateNickname } from '@/services/contentFilter'
import type { QuizHistoryItem as UserQuizHistoryItem } from '@/types/user'
import type { Question, AnswerRecord, QuizGenerateResult, ReportGenerateResult } from '@/types/quiz'

export default function MinePage() {
  const isLoggedIn = useUserStore(s => s.isLoggedIn)
  const user = useUserStore(s => s.user)
  const stats = useUserStore(s => s.stats)
  const refreshProfile = useUserStore(s => s.refreshProfile)
  const updateNickname = useUserStore(s => s.updateNickname)
  const updateAvatar = useUserStore(s => s.updateAvatar)
  const loading = useUserStore(s => s.loading)

  const quizStoreHistory = useQuizStore(s => s.history)
  const loadHistory = useQuizStore(s => s.loadHistory)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const setRecords = useQuizStore(s => s.setRecords)
  const setReport = useQuizStore(s => s.setReport)

  const [userHistory, setUserHistory] = useState<UserQuizHistoryItem[] | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [nickModalOpen, setNickModalOpen] = useState(false)
  const [nickInput, setNickInput] = useState('')
  const [nickInputFocused, setNickInputFocused] = useState(false)
  const [avatarUploading, setAvatarUploading] = useState(false)
  const [failedAvatarUrl, setFailedAvatarUrl] = useState('')
  const avatarUploadPending = useRef(false)
  const avatarUrl = getAvatarUrl(user?.avatar_url)
  const isWeapp = process.env.TARO_ENV === 'weapp'

  useDidShow(async () => {
    loadHistory()
    const userState = useUserStore.getState()
    if (!userState.isLoggedIn) await userState.wxLoginFlow()
    if (useUserStore.getState().isLoggedIn) {
      try { await useUserStore.getState().refreshProfile() } catch (_) { /* noop */ }
      await loadUserQuizzes()
    }
  })

  useEffect(() => {
    const run = async () => {
      const userState = useUserStore.getState()
      if (!userState.isLoggedIn) await userState.wxLoginFlow()
      if (useUserStore.getState().isLoggedIn) await loadUserQuizzes()
    }
    run().catch(err => console.warn('[Mine] mount refresh err:', err))
  }, [])

  const loadUserQuizzes = async () => {
    try {
      setHistoryLoading(true)
      const res = await API.listQuizzes(1, 20)
      if (res.code === 0 && res.data) {
        setUserHistory(res.data.items || [])
      } else {
        setUserHistory(null)
      }
    } catch (err) {
      console.error('[Mine] list quizzes error:', err)
      setUserHistory(null)
    } finally {
      setHistoryLoading(false)
    }
  }

  const displayStats = useMemo(() => {
    if (stats) {
      return {
        quiz_count: stats.quiz_count || 0,
        correct_count: stats.correct_count || 0,
        avg_accuracy: stats.average_accuracy || 0,
        total_questions: stats.total_questions || 0,
      }
    }
    const list = quizStoreHistory || []
    const total = list.length
    const correct = list.reduce((s, x) => s + (x.correct || 0), 0)
    const questions = list.reduce((s, x) => s + (x.total || 0), 0)
    const acc = questions ? Math.round((correct / questions) * 100) : 0
    return { quiz_count: total, correct_count: correct, avg_accuracy: acc, total_questions: questions }
  }, [stats, quizStoreHistory])

  const displayHistory = useMemo(() => {
    if (userHistory && userHistory.length) {
      return userHistory.map(x => ({
        id: x.quiz_id,
        title: x.title,
        correct: x.correct_count,
        total: x.question_count,
        accuracy: x.accuracy,
        created_at: x.created_at,
        xp: x.total_xp,
        _fromUser: true as const,
      }))
    }
    return (quizStoreHistory || []).map(x => ({
      id: x.id,
      title: x.title,
      correct: x.correct,
      total: x.total,
      accuracy: x.accuracy,
      created_at: x.created_at,
      xp: undefined as number | undefined,
      _fromUser: false as const,
    }))
  }, [userHistory, quizStoreHistory])

  const openEditNickname = () => {
    setNickInput(user?.nickname || '')
    setNickInputFocused(false)
    setNickModalOpen(true)
  }

  const saveAvatar = async (filePath: string) => {
    if (!filePath || avatarUploadPending.current) return
    avatarUploadPending.current = true
    setAvatarUploading(true)
    try {
      const ok = await updateAvatar(filePath)
      if (ok) {
        setFailedAvatarUrl('')
        Taro.showToast({ title: '头像已更新', icon: 'success' })
      }
    } finally {
      avatarUploadPending.current = false
      setAvatarUploading(false)
    }
  }

  const chooseAvatar = async () => {
    if (!useUserStore.getState().isLoggedIn) {
      toastError('请先登录后再修改头像')
      return
    }
    if (isWeapp || avatarUploadPending.current) return
    try {
      const result = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
      })
      if (result.tempFilePaths[0]) await saveAvatar(result.tempFilePaths[0])
    } catch (err) {
      const message = (err as { errMsg?: string })?.errMsg || ''
      if (!/cancel/i.test(message)) toastError('无法选择头像，请检查相册权限后重试')
    }
  }

  const saveNickname = async (value: unknown) => {
    if (loading) return
    // Use the native form value after WeChat nickname selection and review.
    const name = typeof value === 'string' ? value.trim() : ''
    if (!name) {
      toastError('昵称不能为空')
      return
    }
    if (name.length > 20) {
      toastError('昵称不能超过 20 个字符')
      return
    }
    if (!validateNickname(name)) return
    const ok = await updateNickname(name)
    if (ok) setNickModalOpen(false)
  }

  const accuracyClass = (acc: number) =>
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low

  const openHistoryItem = useCallback(async (item: typeof displayHistory[number]) => {
    if (item._fromUser) {
      Taro.showLoading({ title: '加载中...', mask: true })
      try {
        const res = await API.getQuizDetail(item.id)
        if (res.code !== 0 || !res.data) {
          toastError(res.message || '加载失败，请重试')
          return
        }
        const detail = res.data
        const fakeQuiz: QuizGenerateResult = {
          quiz_id: detail.quiz_id,
          title: detail.title,
          questions: detail.questions as Question[],
        }
        setQuiz(fakeQuiz)
        setRecords(detail.answer_records as AnswerRecord[])
        setReport(detail.report as ReportGenerateResult)
        useQuizStore.getState().saveReportPayload({
          quiz: { questions: detail.questions as Question[] },
          answer_records: detail.answer_records as AnswerRecord[],
          report: detail.report as ReportGenerateResult,
        })
        Taro.navigateTo({ url: '/pages/report/index' })
      } catch (err) {
        console.error('[Mine] get detail error:', err)
        toastError('加载失败，请稍后重试')
      } finally {
        Taro.hideLoading()
      }
      return
    }
    const localItem = (quizStoreHistory || []).find(x => x.id === item.id)
    if (!localItem?.quiz_snapshot) return
    const snap = localItem.quiz_snapshot
    setQuiz(snap.quiz as QuizGenerateResult)
    setRecords(snap.answer_records)
    setReport(snap.report as ReportGenerateResult)
    useQuizStore.getState().saveReportPayload({
      quiz: { questions: (snap.quiz as QuizGenerateResult).questions },
      answer_records: snap.answer_records,
      report: snap.report as ReportGenerateResult,
    })
    Taro.navigateTo({ url: '/pages/report/index' })
  }, [quizStoreHistory, setQuiz, setRecords, setReport])

  return (
    <View className={styles.page}>
      <View className={styles.profile}>
        <Button
          className={styles.avatar}
          openType={isWeapp && isLoggedIn ? 'chooseAvatar' : undefined}
          onChooseAvatar={e => saveAvatar(e.detail.avatarUrl)}
          onClick={chooseAvatar}
          disabled={avatarUploading || loading}
          hoverClass='none'
          ariaLabel='修改头像'
        >
          {avatarUrl && avatarUrl !== failedAvatarUrl
            ? <Image
                className={styles.avatarImg}
                src={avatarUrl}
                mode='aspectFill'
                onError={() => setFailedAvatarUrl(avatarUrl)}
              />
            : <Text>{(user?.nickname || '学').slice(0, 1)}</Text>}
          {avatarUploading && <Text className={styles.avatarPending}>上传中</Text>}
        </Button>
        <View className={styles.info}>
          <View className={styles.nameRow} onClick={openEditNickname}>
            <Text className={styles.name}>{user?.nickname || '学习者'}</Text>
            <View className={styles.editIcon}>✏️</View>
          </View>
          <Text className={styles.desc}>
            {isLoggedIn
              ? `累计闯关 ${displayStats.quiz_count} 次 · 总 XP ${user?.total_xp ?? 0}`
              : `本地累计闯关 ${displayStats.quiz_count} 次`}
          </Text>
        </View>
      </View>

      <View className={styles.stats}>
        <View className={styles.item}>
          <Text className={styles.num}>{displayStats.quiz_count}</Text>
          <Text className={styles.label}>总闯关次数</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num}>{displayStats.avg_accuracy}%</Text>
          <Text className={styles.label}>平均正确率</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num}>{displayStats.correct_count}</Text>
          <Text className={styles.label}>答对题数</Text>
        </View>
      </View>

      <View className={styles.sectionTitle}>
        <View className={styles.left}>我的闯关历史</View>
        <View className={styles.right} onClick={loadUserQuizzes}>
          {historyLoading ? '加载中...' : '刷新'}
        </View>
      </View>

      <View className={styles.historyList}>
        {!displayHistory.length ? (
          <View className={styles.empty}>还没有闯关记录，去首页生成一套题目吧 ✨</View>
        ) : (
          displayHistory.map(item => (
            <View key={item.id} className={styles.historyCard} onClick={() => openHistoryItem(item)}>
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
                {item.xp != null && (
                  <>
                    <Text>·</Text>
                    <Text className={styles.xpTag}>+{item.xp} XP</Text>
                  </>
                )}
              </View>
            </View>
          ))
        )}
      </View>

      <View className={styles.tip}>
        💡 小提示：登录后你的答题数据和 XP 会自动同步到云端，换设备登录也能查看历史记录。
      </View>

      <AppButton variant='secondary' size='lg' onClick={() => Taro.switchTab({ url: '/pages/index/index' })}>
        去首页开始学习
      </AppButton>

      {nickModalOpen && (
        <View className={styles.modalMask} onClick={() => setNickModalOpen(false)}>
          <Form
            className={styles.modalCard}
            onClick={e => e.stopPropagation()}
            onSubmit={e => saveNickname(e.detail.value?.nickname)}
          >
            <View className={styles.modalHeader}>
              <Text className={styles.modalTitle}>修改昵称</Text>
              <Text className={styles.modalSubtitle}>
                {isWeapp ? '点击输入框可选用微信昵称，也可自行填写' : '取一个你喜欢的名字'}
              </Text>
            </View>
            <View className={styles.modalField}>
              <Input
                name='nickname'
                type={isWeapp ? 'nickname' : 'text'}
                className={classnames(styles.modalInput, nickInputFocused && styles.modalInputFocused)}
                placeholder='请输入昵称'
                placeholderClass={styles.modalPlaceholder}
                value={nickInput}
                onInput={e => setNickInput(e.detail.value)}
                onFocus={() => setNickInputFocused(true)}
                onBlur={e => {
                  setNickInput(e.detail.value)
                  setNickInputFocused(false)
                }}
                disabled={loading}
                maxlength={20}
              />
              <Text className={styles.modalCount}>{nickInput.length}/20</Text>
            </View>
            <View className={styles.modalActions}>
              <AppButton
                variant='secondary'
                size='lg'
                className={classnames(styles.modalBtn, styles.modalCancel)}
                onClick={() => setNickModalOpen(false)}
              >
                取消
              </AppButton>
              <AppButton
                variant='primary'
                size='lg'
                className={classnames(styles.modalBtn, styles.modalSave)}
                loading={loading}
                disabled={loading}
                formType='submit'
              >
                保存
              </AppButton>
            </View>
          </Form>
        </View>
      )}
    </View>
  )
}
