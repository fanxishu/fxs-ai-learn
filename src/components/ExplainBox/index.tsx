import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type ExplainState = 'good' | 'bad'

export interface ExplainBoxProps {
  state?: ExplainState
  title?: string
  text: string
  showBadge?: boolean
}

export default function ExplainBox ({
  state = 'good',
  title,
  text,
  showBadge = true,
}: ExplainBoxProps) {
  const badgeText = title ?? (state === 'good' ? '回答正确' : '回答错误')
  return (
    <View className={styles.wrap}>
      {showBadge && (
        <View className={classnames(styles.badge, styles[`state-${state}`])}>
          <Text>{badgeText}</Text>
        </View>
      )}
      <Text className={styles.text}>
        {text || '解析：请对比正确答案巩固知识点。'}
      </Text>
    </View>
  )
}
