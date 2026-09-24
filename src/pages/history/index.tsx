import React, { useCallback, useMemo, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'
import { AppButton, Chip, ProgressTrack, StateBadge } from '@/components'
import { useQuizStore } from '@/store/quiz'
import type { HistoryItem } from '@/types/quiz'

export default function HistoryPage() {
  const loadHistory = useQuizStore(s => s.loadHistory)
  const clearHistory = useQuizStore(s => s.clearHistory)
  const removeHistoryItem = useQuizStore(s => s.removeHistoryItem)
  const setQuiz = useQuizStore(s => s.setQuiz)
  const setRecords = useQuizStore(s => s.setRecords)
  const setReport = useQuizStore(s => s.setReport)
  const saveQuizSession = useQuizStore(s => s.saveQuizSession)
  const history = useQuizStore(s => s.history)

  const [refreshing, setRefreshing] = useState(false)

  useDidShow(() => {
    loadHistory()
  })

  usePullDownRefresh(async () => {
    setRefreshing(true)
    loadHistory()
    setTimeout(() => {
      Taro.stopPullDownRefresh()
      setRefreshing(false)
    }, 300)
  })

  const list = useMemo<HistoryItem[]>(() => history || [], [history])

  const openReport = useCallback((item: HistoryItem) => {
    if (!item.quiz_snapshot) {
      Taro.showToast({ title: '无详情快照', icon: 'none' })
      return
    }
    setQuiz(item.quiz_snapshot.quiz)
    setRecords(item.quiz_snapshot.answer_records)
    setReport(item.quiz_snapshot.report)
    saveQuizSession({ quiz: item.quiz_snapshot.quiz })
    Taro.navigateTo({ url: '/pages/report/index' })
  }, [setQuiz, setRecords, setReport, saveQuizSession])

  const reopen = useCallback((item: HistoryItem) => {
    if (!item.quiz_snapshot) return
    setQuiz(item.quiz_snapshot.quiz)
    setRecords([])
    setReport(null)
    saveQuizSession({ quiz: item.quiz_snapshot.quiz })
    Taro.navigateTo({ url: '/pages/quiz/index' })
  }, [setQuiz, setRecords, setReport, saveQuizSession])

  const handleClear = async () => {
    if (!list.length) return
    const res = await Taro.showModal({
      title: '确认清空历史',
      content: '清空后无法恢复，是否继续？',
      confirmColor: '#f53f3f',
    })
    if (res.confirm) {
      clearHistory()
      Taro.showToast({ title: '已清空', icon: 'success' })
    }
  }

  const scoreClass = (acc: number) =>
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low

  const avgAcc = useMemo(() => {
    if (!list.length) return 0
    const sum = list.reduce((s, x) => s + x.accuracy, 0)
    return Math.round(sum / list.length)
  }, [list])

  return (
    <View className={styles.page}>
      <View className={styles.header}>
        <View>
          <Text className={styles.title}>历史闯关</Text>
          <View className={styles.sub}>
            共 {list.length} 次 · 平均正确率 {avgAcc}%
          </View>
        </View>
        <View className={styles.actions}>
          <AppButton
            size='md'
            variant='ghost'
            disabled={!list.length}
            onClick={handleClear}
          >
            清空
          </AppButton>
          <AppButton
            size='md'
            variant='secondary'
            onClick={() => Taro.switchTab({ url: '/pages/home/index' })}
          >
            去闯关
          </AppButton>
        </View>
      </View>

      {!list.length ? (
        <View className={styles.empty}>
          <Text className={styles.icon}>📚</Text>
          <Text className={styles.title}>还没有闯关记录</Text>
          <Text className={styles.sub}>去首页输入一个知识点，开启你的第一次 AI 闯关吧！</Text>
          <View className={styles.btnWrap}>
            <AppButton block size='lg' variant='primary' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
              🎯 立即闯关
            </AppButton>
          </View>
        </View>
      ) : (
        <View className={styles.list}>
          {list.map(item => (
            <View key={item.id} className={styles.card} onClick={() => openReport(item)}>
              <View className={styles.top}>
                <Text className={styles.title}>{item.title}</Text>
                <StateBadge kind={item.accuracy >= 60 ? 'good' : 'bad'}>
                  正确率 {item.accuracy}%
                </StateBadge>
              </View>

              <Text className={styles.input}>{item.user_input}</Text>

              <View className={styles.bars}>
                <ProgressTrack percent={item.accuracy} height={10} color={item.accuracy >= 80 ? 'green' : item.accuracy >= 60 ? 'blue' : 'red'} />
              </View>

              <View className={styles.chips}>
                {item.mastered_points?.slice(0, 2).map(p => (
                  <Chip key={`g-${p}`} color='green' size='sm'>✓ {p}</Chip>
                ))}
                {item.weak_points?.slice(0, 2).map(p => (
                  <Chip key={`w-${p}`} color='red' size='sm'>⚠ {p}</Chip>
                ))}
              </View>

              <View className={styles.meta}>
                <View className={styles.left}>
                  <Text className={classnames(styles.score, scoreClass(item.accuracy))}>
                    {item.correct}/{item.total} 题
                  </Text>
                  <Text>·</Text>
                  <Text>{new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString().slice(0, 5)}</Text>
                </View>
                <View style={{ display: 'flex', gap: 16 }} onClick={(e) => e.stopPropagation()}>
                  <AppButton
                    size='md'
                    variant='secondary'
                    onClick={(e) => {
                      (e as any).stopPropagation?.();
                      reopen(item)
                    }}
                  >
                    再闯一次
                  </AppButton>
                  <AppButton
                    size='md'
                    variant='ghost'
                    onClick={(e) => {
                      (e as any).stopPropagation?.();
                      Taro.showActionSheet({
                        itemList: ['删除该记录'],
                      }).then(({ tapIndex }) => {
                        if (tapIndex === 0) removeHistoryItem(item.id)
                      }).catch(() => {})
                    }}
                  >
                    更多
                  </AppButton>
                </View>
              </View>
            </View>
          ))}
        </View>
      )}

      {refreshing && <View />}
    </View>
  )
}
