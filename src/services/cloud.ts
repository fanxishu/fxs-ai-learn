import Taro from '@tarojs/taro'

const getEnv = (key: string, fallback: string = ''): string => {
  try {
    if (typeof process !== 'undefined' && (process as any).env && (process as any).env[key] != null) {
      return String((process as any).env[key])
    }
  } catch (_) { /* noop */ }
  return fallback
}

const isWeapp = getEnv('TARO_ENV') === 'weapp'

export async function callFunction<T = any>(
  name: string,
  data?: Record<string, any>
): Promise<T> {
  if (!isWeapp) {
    const mockModule = await import(`../data/${name}`)
    return mockModule.default(data) as T
  }
  const res = await Taro.cloud.callFunction({ name, data })
  const result = res.result as { code: number; message: string; data: T }
  if (result.code !== 0) {
    console.error(`[Cloud] ${name} failed:`, result.message)
    throw new Error(result.message || '请求失败')
  }
  return result.data
}

export function getDatabase() {
  if (!isWeapp) {
    return null
  }
  return Taro.cloud.database()
}
