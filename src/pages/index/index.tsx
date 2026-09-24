import React, { useEffect } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import styles from './index.module.scss'
import { AppButton } from '@/components'

export default function IndexPage() {
  useEffect(() => {
    const t = setTimeout(() => {
      Taro.switchTab({ url: '/pages/home/index' })
    }, 800)
    return () => clearTimeout(t)
  }, [])

  return (
    <View className={styles.page}>
      <Text className={styles.emoji}>🐟</Text>
      <Text className={styles.title}>鱼皮 AI 闯关</Text>
      <Text className={styles.sub}>万物皆可闯关，把任何知识点都变成趣味问答游戏。</Text>
      <View className={styles.cards}>
        <View className={styles.pill}>AI 出题</View>
        <View className={styles.pill}>即时讲解</View>
        <View className={styles.pill}>复盘报告</View>
      </View>
      <View className={styles.btnWrap}>
        <AppButton block size='xl' variant='primary' onClick={() => Taro.switchTab({ url: '/pages/home/index' })}>
          🚀 立即开始
        </AppButton>
      </View>
    </View>
  )
}
