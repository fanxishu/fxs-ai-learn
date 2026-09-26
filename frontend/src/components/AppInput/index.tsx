import { useState } from 'react'
import { View, Text, Textarea } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export interface AppInputProps {
  label?: string
  placeholder?: string
  value: string
  onChange: (val: string) => void
  min?: number
  max?: number
  minHeight?: number
  disabled?: boolean
}

export default function AppInput ({
  label,
  placeholder = '请输入学习内容，比如：Python 基础语法',
  value,
  onChange,
  min,
  max,
  minHeight = 320,
  disabled = false,
}: AppInputProps) {
  const count = value.length
  const warnMax = typeof max === 'number' && count > max
  const warnMin = typeof min === 'number' && count > 0 && count < min

  return (
    <View className={styles.wrap}>
      {label && <Text className={styles.label}>{label}</Text>}
      <View
        className={classnames(styles.box, warnMax && styles.warn, disabled && styles.disabled)}
      >
        <Textarea
          className={styles.textarea}
          placeholder={placeholder}
          placeholderClass={styles.placeholder}
          value={value}
          onInput={e => onChange(e.detail.value)}
          maxlength={max ?? 500}
          disabled={disabled}
          style={{ minHeight: `${minHeight}rpx` }}
          showConfirmBar={false}
          autoHeight
        />
      </View>
      {(typeof min === 'number' || typeof max === 'number') && (
        <View className={styles.count}>
          <Text className={classnames(warnMin && styles.warnText, warnMax && styles.warnText)}>
            {count}
            {typeof max === 'number' ? ` / ${max}` : ''}
          </Text>
          {warnMin && <Text className={styles.warnText}>  最少 {min} 字</Text>}
          {warnMax && <Text className={styles.warnText}>  已超出 {max} 字</Text>}
        </View>
      )}
    </View>
  )
}
