/**
 * 方案文档 §16.1 统一错误码 — 必须与后端 backend/app/core/exceptions.py::ErrorCode
 * 的名称、数值完全一致，避免两端对不上。
 */
export const ErrorCode = {
  SUCCESS: 0,

  // 1000~1999：客户端 / 参数错误
  PARAM_MISSING: 1001,
  PARAM_INVALID: 1002,
  INPUT_TOO_LONG: 1003,
  INPUT_TOO_SHORT: 1004,

  // 2000~2999：鉴权 / 用户错误
  UNAUTHORIZED: 2001,
  TOKEN_EXPIRED: 2002,
  NOT_LOGGED_IN: 2003,

  // 3000~3999：内容安全错误
  INPUT_CONTENT_VIOLATION: 3001,
  OUTPUT_CONTENT_VIOLATION: 3002,

  // 4000~4999：业务逻辑错误
  QUIZ_NOT_FOUND: 4001,
  ANSWER_RECORD_INVALID: 4002,

  // 5000~5999：服务端 / AI 调用错误
  INTERNAL_SERVER_ERROR: 5000,
  DEEPSEEK_TIMEOUT: 5001,
  DEEPSEEK_FORMAT_ERROR: 5002,
  DEEPSEEK_RETRY_EXHAUSTED: 5003,
} as const;

export type ErrorCode = typeof ErrorCode[keyof typeof ErrorCode];

/**
 * 通用 API 响应包装（AC-14：接口永远 HTTP 200，用 code 承载业务结果）。
 * 与 backend/app/models/common.py::ApiResponse 字段一一对应。
 */
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data?: T | null;
  request_id?: string;
}

/** 错误码 -> 用户文案映射（Toast 直接用） */
export const ERROR_TOAST: Record<number, string> = {
  [ErrorCode.PARAM_MISSING]: '请求参数缺失，请刷新页面重试',
  [ErrorCode.PARAM_INVALID]: '参数格式错误，请检查输入',
  [ErrorCode.INPUT_TOO_LONG]: '输入内容过长，请删减到 500 字以内',
  [ErrorCode.INPUT_TOO_SHORT]: '输入内容过短，请提供更详细的学习主题',
  [ErrorCode.UNAUTHORIZED]: '请先登录后再使用',
  [ErrorCode.TOKEN_EXPIRED]: '登录已过期，请重新登录',
  [ErrorCode.NOT_LOGGED_IN]: '请先登录后再使用本功能',
  [ErrorCode.INPUT_CONTENT_VIOLATION]: '输入内容不合规，请修改后重试',
  [ErrorCode.OUTPUT_CONTENT_VIOLATION]: '生成内容包含违规信息，请重试',
  [ErrorCode.QUIZ_NOT_FOUND]: '题库不存在或已过期，请重新生成',
  [ErrorCode.ANSWER_RECORD_INVALID]: '答题记录不完整，请完成所有题目',
  [ErrorCode.INTERNAL_SERVER_ERROR]: '服务出了点小差，请稍后重试',
  [ErrorCode.DEEPSEEK_TIMEOUT]: 'AI 响应超时，请稍后重试',
  [ErrorCode.DEEPSEEK_FORMAT_ERROR]: 'AI 输出异常，请稍后重试',
  [ErrorCode.DEEPSEEK_RETRY_EXHAUSTED]: '生成失败，请稍后重试',
};
