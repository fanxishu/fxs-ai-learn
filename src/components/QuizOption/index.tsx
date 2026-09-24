import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type QuizOptionState = 'normal' | 'selected' | 'correct' | 'wrong'

export interface QuizOptionProps {
  keyLabel: string
  text: string
  state?: QuizOptionState
  onClick?: () => void
  disabled?: boolean
}

export default function QuizOption ({
  keyLabel,
  text,
  state = 'normal',
  onClick,
  disabled = false,
}: QuizOptionProps) {
  const selected = state === 'selected'
  return (
    <View
      className={classnames(styles.opt, styles[`state-${state}`], disabled && styles.disabled)}
      onClick={disabled ? undefined : onClick}
    >
      <View className={classnames(styles.optKey, selected && styles.optKeySelected)}>
        <Text>{keyLabel}</Text>
      </View>
      <Text className={styles.optText}>{text}</Text>
    </View>
  )
}
