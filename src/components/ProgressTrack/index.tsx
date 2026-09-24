import { View } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type ProgressTrackColor = 'orange' | 'blue' | 'green' | 'red'

export interface ProgressTrackProps {
  percent: number
  height?: number
  color?: ProgressTrackColor
  showText?: boolean
  textLeft?: React.ReactNode
  className?: string
}

export default function ProgressTrack ({
  percent,
  height = 14,
  color = 'orange',
  showText = false,
  textLeft,
  className = '',
}: ProgressTrackProps) {
  const w = Math.max(0, Math.min(100, Math.round(percent)))
  return (
    <View className={classnames(styles.wrap, className)}>
      {showText && <View className={styles.textLeft}>{textLeft}</View>}
      <View className={styles.track} style={{ height: `${height * 2}rpx` }}>
        <View
        className={classnames(styles.fill, styles[`color-${color}`])} style={{ width: `${w}%` }} />
      </View>
    </View>
  )
}
