from __future__ import annotations

from typing import Any, Optional
from fastapi import HTTPException, status


class FishAIException(HTTPException):
    """Base exception for Fish AI project."""

    code: int = 1000
    message: str = "服务内部错误"

    def __init__(
        self,
        code: Optional[int] = None,
        message: Optional[str] = None,
        detail: Any = None,
    ) -> None:
        self.code = code or self.__class__.code
        self.message = message or self.__class__.message
        super().__init__(
            status_code=status.HTTP_200_OK,
            detail=detail or self.message,
        )


class ValidationError(FishAIException):
    code = 4000
    message = "参数校验失败"


class QuizGenerateError(FishAIException):
    code = 5001
    message = "生成题目失败，请重试"


class ReportGenerateError(FishAIException):
    code = 5002
    message = "生成报告失败，请重试"


class SensitiveContentError(FishAIException):
    code = 4001
    message = "输入包含违规内容，请修改后重试"


AI_GENERATE_FAILED_CODE = 5001
