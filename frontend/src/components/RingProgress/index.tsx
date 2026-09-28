import { View, Text } from '@tarojs/components'
import styles from './index.module.scss'

export interface RingProgressProps {
  accuracy: number
  size?: number
  strokeWidth?: number
  showLabel?: boolean
  unit?: string
}

/**
 * 分数徽章。小程序端 SVG 圆环不稳定，这里用白底圆形数字保证始终可读。
 */
export default function RingProgress ({
  accuracy,
  size = 84,
  showLabel = true,
  unit = '分',
}: RingProgressProps) {
  const acc = Math.max(0, Math.min(100, Math.round(accuracy)))
  const toneClass =
    acc >= 80 ? styles.high : acc >= 60 ? styles.mid : styles.low
  const rpx = size * 2

  return (
    <View
      className={`${styles.wrap} ${toneClass}`}
      style={{ width: `${rpx}rpx`, height: `${rpx}rpx` }}
    >
      {showLabel && (
        <View className={styles.inner}>
          <Text className={styles.num}>{acc}</Text>
          <Text className={styles.unit}>{unit}</Text>
        </View>
      )}
    </View>
  )
}
