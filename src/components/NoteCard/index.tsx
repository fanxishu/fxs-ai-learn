import { View, Text } from '@tarojs/components'
import classnames from 'classnames'
import styles from './index.module.scss'

export type NoteCardVariant = 'summary' | 'advice' | 'quote' | 'mastery-good' | 'mastery-weak'

export interface NoteCardProps {
  variant?: NoteCardVariant
  children: React.ReactNode
  index?: number
  title?: string
  list?: string[]
  emptyText?: string
  listItemClass?: 'good' | 'weak'
}

export default function NoteCard ({
  variant = 'advice',
  children,
  index,
  title,
  list,
  emptyText = '暂无数据',
  listItemClass,
}: NoteCardProps) {
  const renderBody = () => {
    if (list) {
      if (!list.length) return <Text className={styles.empty}>{emptyText}</Text>
      return (
        <View className={styles.list}>
          {list.map((p, i) => (
            <Text
              key={i}
              className={
                listItemClass === 'weak'
                  ? styles.pointWeak
                  : listItemClass === 'good'
                    ? styles.pointGood
                    : styles.pointDefault
              }
            >
              • {p}
            </Text>
          ))}
        </View>
      )
    }
    if (variant === 'quote') {
      return (
        <>
          <Text className={styles.quoteMark}>"</Text>
          <Text className={styles.quoteText}>{children}</Text>
          <Text className={styles.quoteMark}>"</Text>
        </>
      )
    }
    if (variant === 'summary' && typeof index === 'number') {
      return (
        <View className={styles.summaryRow}>
          <View className={styles.summaryIdx}>{index}</View>
          <Text className={styles.summaryText}>{children}</Text>
        </View>
      )
    }
    return <Text className={styles.adviceText}>{children}</Text>
  }

  return (
    <View className={classnames(styles.card, styles[`variant-${variant}`])}>
      {title && <Text className={styles.title}>{title}</Text>}
      {renderBody()}
    </View>
  )
}
