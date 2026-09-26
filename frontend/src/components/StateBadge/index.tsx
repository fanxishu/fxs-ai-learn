import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type StateBadgeKind = 'good' | 'bad' | 'info'

export interface StateBadgeProps {
  children: React.ReactNode
  kind?: StateBadgeKind
}

export default function StateBadge ({ children, kind = 'info' }: StateBadgeProps) {
  return (
    <View className={classnames(styles.badge, styles[`kind-${kind}`])}>
      <Text>{children}</Text>
    </View>
  )
}
