import { View, Text, Button } from '@tarojs/components'
import Taro from '@tarojs/taro'
import classnames from 'classnames'
import styles from './index.module.scss'

export type AppButtonVariant = 'primary' | 'secondary' | 'ghost'
export type AppButtonSize = 'md' | 'lg' | 'xl'

export interface AppButtonProps {
  children: React.ReactNode
  variant?: AppButtonVariant
  size?: AppButtonSize
  block?: boolean
  disabled?: boolean
  loading?: boolean
  onClick?: () => void | Promise<void>
  className?: string
}

export default function AppButton ({
  children,
  variant = 'primary',
  size = 'lg',
  block = false,
  disabled = false,
  loading = false,
  onClick,
  className = '',
}: AppButtonProps) {
  const cls = classnames(
    styles.btn,
    styles[`variant-${variant}`],
    styles[`size-${size}`],
    block && styles.block,
    disabled && styles.disabled,
    className,
  )

  const handle = async () => {
    if (disabled || loading) return
    try {
      await onClick?.()
    } catch (err) {
      Taro.showToast({ title: (err as Error)?.message || '操作失败', icon: 'none' })
    }
  }

  return (
    <Button
      className={cls}
      disabled={disabled}
      loading={loading}
      onClick={handle}
    >
      {children}
    </Button>
  )
}
