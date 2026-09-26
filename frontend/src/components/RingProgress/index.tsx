import { useMemo } from 'react'
import { View, Text } from '@tarojs/components'
import styles from './index.module.scss'

export interface RingProgressProps {
  accuracy: number
  size?: number
  strokeWidth?: number
  showLabel?: boolean
  unit?: string
}

export default function RingProgress ({
  accuracy,
  size = 260,
  strokeWidth = 10,
  showLabel = true,
  unit = '分',
}: RingProgressProps) {
  const acc = Math.max(0, Math.min(100, Math.round(accuracy)))
  const scoreColor =
    acc >= 80 ? $green : acc >= 60 ? $orange : $red

  const viewBox = 100
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const ratio = (strokeWidth * viewBox) / size
  const dashOffset = useMemo(
    () => Math.round(circumference * (1 - acc / 100)),
    [circumference, acc],
  )

  return (
    <View className={styles.wrap} style={{ width: `${size * 2}rpx`, height: `${size * 2}rpx` }}>
      <svg viewBox={`0 0 ${viewBox} ${viewBox}`} className={styles.ring}>
        <circle
          cx={viewBox / 2}
          cy={viewBox / 2}
          r={radius}
          stroke='#f0ebe0'
          strokeWidth={ratio}
          fill='none'
        />
        <circle
          cx={viewBox / 2}
          cy={viewBox / 2}
          r={radius}
          stroke={scoreColor}
          strokeWidth={ratio}
          fill='none'
          strokeLinecap='round'
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${viewBox / 2} ${viewBox / 2})`}
          style={{ transition: 'stroke-dashoffset 600ms ease' }}
        />
      </svg>
      {showLabel && (
        <View className={styles.inner}>
          <Text className={styles.num} style={{ color: scoreColor }}>{acc}</Text>
          <Text className={styles.unit}>{unit}</Text>
        </View>
      )}
    </View>
  )
}

const $orange = '#ff7a2f'
const $green = '#2e9e71'
const $red = '#ff6f5d'
