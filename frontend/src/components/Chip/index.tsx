import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type ChipColor = 'orange' | 'blue' | 'purple' | 'green' | 'red' | 'soft-blue' | 'soft-orange'
export type ChipSize = 'sm' | 'md'

export interface ChipProps {
  children: React.ReactNode
  color?: ChipColor
  size?: ChipSize
}

export default function Chip ({ children, color = 'orange', size = 'md' }: ChipProps) {
  return (
    <View className={classnames(styles.chip, styles[`color-${color}`], styles[`size-${size}`])}>
      <Text>{children}</Text>
    </View>
  )
}
