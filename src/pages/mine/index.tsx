import React, { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import styles from './index.module.scss'
import { AppButton } from '@/components'
import { useQuizStore } from '@/store/quiz'

export default function MinePage() {
  const loadHistory = useQuizStore(s => s.loadHistory)
  const history = useQuizStore(s => s.history)
  useDidShow(() => loadHistory())

  const list = history || []
  const stats = useMemo(() => {
    const total = list.length
    const correct = list.reduce((s, x) => s + x.correct, 0)
    const questions = list.reduce((s, x) => s + x.total, 0)
    const acc = questions ? Math.round((correct / questions) * 100) : 0
    return { total, correct, questions, acc }
  }, [list])

  const MENU = [
    { icon: '🏆', title: '学习成就', desc: '查看里程碑与徽章', tag: '敬请期待' },
    { icon: '📝', title: '错题本', desc: '针对薄弱点专项练习', tag: '敬请期待' },
    { icon: '⚙️', title: '设置', desc: '偏好、通知、关于我们', tag: '敬请期待' },
  ]

  return (
    <View className={styles.page}>
      <View className={styles.profile}>
        <View className={styles.avatar}>🐟</View>
        <View className={styles.info}>
          <Text className={styles.name}>学习爱好者</Text>
          <Text className={styles.desc}>累计闯关 {stats.total} 次 · 平均正确率 {stats.acc}%</Text>
        </View>
      </View>

      <View className={styles.stats}>
        <View className={styles.item}>
          <Text className={styles.num}>{stats.total}</Text>
          <Text className={styles.label}>总闯关次数</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num}>{stats.acc}%</Text>
          <Text className={styles.label}>平均正确率</Text>
        </View>
        <View className={styles.item}>
          <Text className={styles.num}>{stats.questions}</Text>
          <Text className={styles.label}>已答题数</Text>
        </View>
      </View>

      <View className={styles.menuCard}>
        {MENU.map(m => (
          <View
            key={m.title}
            className={styles.menuItem}
            onClick={() => Taro.showToast({ title: '功能即将上线', icon: 'none' })}
          >
            <View className={styles.icon}>{m.icon}</View>
            <View className={styles.content}>
              <Text className={styles.title}>{m.title}</Text>
              <Text className={styles.desc}>{m.desc}</Text>
            </View>
            <Text className={styles.tag}>{m.tag}</Text>
            <Text className={styles.arrow}>›</Text>
          </View>
        ))}
      </View>

      <View className={styles.tip}>
        💡 小提示：本小程序不强制登录，你的闯关记录保存在本地。建议每完成 5 次闯关后，回到「历史」页复盘自己的薄弱知识点。
      </View>

      <AppButton variant='secondary' size='lg' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
        去首页开始学习
      </AppButton>
    </View>
  )
}
