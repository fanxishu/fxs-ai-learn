import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type CoinBadgeVariant = 'solid' | 'soft' | 'pill'

export interface CoinBadgeProps {
  children: React.ReactNode
  variant?: CoinBadgeVariant
}

export default function CoinBadge ({ children, variant = 'solid' }: CoinBadgeProps) {
  return (
    <View className={classnames(styles.badge, styles[`variant-${variant}`])}>
      <View className={styles.icon}>🐟</View>
      <Text className={styles.text}>{children}</Text>
    </View>
  )
}
