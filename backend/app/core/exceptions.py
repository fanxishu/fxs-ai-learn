from __future__ import annotations

from enum import IntEnum
from typing import Any, Optional
from fastapi import status as http_status
from fastapi import HTTPException


class ErrorCode(IntEnum):
    """
    方案文档 §16.1 统一错误码枚举。
    数值 / 名称必须与前端 frontend/src/types/common.ts 的 ErrorCode 完全一致。
    """
    SUCCESS = 0

    # 1000~1999：客户端 / 参数错误
    PARAM_MISSING = 1001
    PARAM_INVALID = 1002
    INPUT_TOO_LONG = 1003
    INPUT_TOO_SHORT = 1004

    # 2000~2999：鉴权 / 用户错误
    UNAUTHORIZED = 2001
    TOKEN_EXPIRED = 2002

    # 3000~3999：内容安全错误
    INPUT_CONTENT_VIOLATION = 3001
    OUTPUT_CONTENT_VIOLATION = 3002

    # 4000~4999：业务逻辑错误
    QUIZ_NOT_FOUND = 4001
    ANSWER_RECORD_INVALID = 4002

    # 5000~5999：服务端 / AI 调用错误
    INTERNAL_SERVER_ERROR = 5000
    DEEPSEEK_TIMEOUT = 5001
    DEEPSEEK_FORMAT_ERROR = 5002
    DEEPSEEK_RETRY_EXHAUSTED = 5003


class FishAIException(HTTPException):
    """Base exception for Fish AI project — 永远返回 HTTP 200，ApiResponse.code 承载错误码。"""

    code: int = int(ErrorCode.INTERNAL_SERVER_ERROR)
    message: str = "服务内部错误"

    def __init__(
        self,
        code: Optional[int] = None,
        message: Optional[str] = None,
        detail: Any = None,
    ) -> None:
        self.code = code if code is not None else self.__class__.code
        self.message = message if message is not None else self.__class__.message
        super().__init__(
            status_code=http_status.HTTP_200_OK,
            detail=detail or self.message,
        )


# ============ 1000 参数错误 ============
class ParamMissingError(FishAIException):
    code = int(ErrorCode.PARAM_MISSING)
    message = "必要参数缺失"


class ParamInvalidError(FishAIException):
    code = int(ErrorCode.PARAM_INVALID)
    message = "参数格式错误"


class InputTooLongError(FishAIException):
    code = int(ErrorCode.INPUT_TOO_LONG)
    message = "输入内容过长，请删减后重试"


class InputTooShortError(FishAIException):
    code = int(ErrorCode.INPUT_TOO_SHORT)
    message = "输入内容过短，请提供更详细的学习主题"


# ============ 2000 鉴权错误 ============
class UnauthorizedError(FishAIException):
    code = int(ErrorCode.UNAUTHORIZED)
    message = "请先登录"


class TokenExpiredError(FishAIException):
    code = int(ErrorCode.TOKEN_EXPIRED)
    message = "登录状态已过期，请重新登录"


# ============ 3000 内容安全错误 ============
class InputContentViolationError(FishAIException):
    code = int(ErrorCode.INPUT_CONTENT_VIOLATION)
    message = "输入内容不合规，请修改后重试"


class OutputContentViolationError(FishAIException):
    code = int(ErrorCode.OUTPUT_CONTENT_VIOLATION)
    message = "生成内容包含违规信息，请重试"


# ============ 4000 业务逻辑错误 ============
class QuizNotFoundError(FishAIException):
    code = int(ErrorCode.QUIZ_NOT_FOUND)
    message = "题库不存在或已过期，请重新生成"


class AnswerRecordInvalidError(FishAIException):
    code = int(ErrorCode.ANSWER_RECORD_INVALID)
    message = "答题记录不完整，请完成全部题目后再提交"


# ============ 5000 服务端 / AI 调用错误 ============
class InternalServerError(FishAIException):
    code = int(ErrorCode.INTERNAL_SERVER_ERROR)
    message = "服务内部错误，请稍后重试"


class DeepSeekTimeoutError(FishAIException):
    code = int(ErrorCode.DEEPSEEK_TIMEOUT)
    message = "AI 服务响应超时，请稍后重试"


class DeepSeekFormatError(FishAIException):
    code = int(ErrorCode.DEEPSEEK_FORMAT_ERROR)
    message = "AI 输出格式异常，请稍后重试"


class DeepSeekRetryExhaustedError(FishAIException):
    code = int(ErrorCode.DEEPSEEK_RETRY_EXHAUSTED)
    message = "生成失败，请稍后重试"


# 兼容旧常量引用
AI_GENERATE_FAILED_CODE = int(ErrorCode.DEEPSEEK_TIMEOUT)

# ============================================================
# 旧命名兼容别名（routes 仍引用 SensitiveContentError / ValidationError 等）
# ============================================================
SensitiveContentError = InputContentViolationError
ValidationError = ParamInvalidError

# 这两个旧类在 quiz_chain 和 route 里被 raise，保留旧名但行为使用新的错误码
class _OldNamedQuizGenerateError(DeepSeekRetryExhaustedError):
    code = int(ErrorCode.DEEPSEEK_RETRY_EXHAUSTED)
    message = "生成题目失败，请重试"

class _OldNamedReportGenerateError(DeepSeekRetryExhaustedError):
    code = int(ErrorCode.DEEPSEEK_RETRY_EXHAUSTED)
    message = "生成报告失败，请重试"

QuizGenerateError = _OldNamedQuizGenerateError
ReportGenerateError = _OldNamedReportGenerateError
