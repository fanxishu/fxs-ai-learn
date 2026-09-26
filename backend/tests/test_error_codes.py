"""Task5 - 错误码标准化 13 条两端对齐（3 cases）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.exceptions import (
    ErrorCode,
    FishAIException,
    InputTooShortError,
    InputContentViolationError,
    QuizNotFoundError,
    DeepSeekRetryExhaustedError,
)


class TestErrorCodeEnum:
    EXPECTED = {
        "SUCCESS": 0,
        "PARAM_MISSING": 1001,
        "PARAM_INVALID": 1002,
        "INPUT_TOO_LONG": 1003,
        "INPUT_TOO_SHORT": 1004,
        "UNAUTHORIZED": 2001,
        "TOKEN_EXPIRED": 2002,
        "INPUT_CONTENT_VIOLATION": 3001,
        "OUTPUT_CONTENT_VIOLATION": 3002,
        "QUIZ_NOT_FOUND": 4001,
        "ANSWER_RECORD_INVALID": 4002,
        "INTERNAL_SERVER_ERROR": 5000,
        "DEEPSEEK_TIMEOUT": 5001,
        "DEEPSEEK_FORMAT_ERROR": 5002,
        "DEEPSEEK_RETRY_EXHAUSTED": 5003,
    }

    def test_all_16_error_codes_named_correctly(self):
        for name, value in self.EXPECTED.items():
            assert hasattr(ErrorCode, name), f"缺少错误码 {name}"
            assert int(ErrorCode[name]) == value, (
                f"错误码 {name} 数值不一致：期望 {value}，实际 {int(ErrorCode[name])}"
            )
        # 不允许 Enum 多额外未声明项
        present = {m.name: m.value for m in ErrorCode}
        assert present == self.EXPECTED, "错误码集合与方案文档 §16.1 不一致"

    def test_exception_subclass_inherits_code(self):
        # 每个具体异常的 code 必须等于对应的 ErrorCode 数值
        assert InputTooShortError.code == int(ErrorCode.INPUT_TOO_SHORT)
        assert InputContentViolationError.code == int(ErrorCode.INPUT_CONTENT_VIOLATION)
        assert QuizNotFoundError.code == int(ErrorCode.QUIZ_NOT_FOUND)
        assert DeepSeekRetryExhaustedError.code == int(ErrorCode.DEEPSEEK_RETRY_EXHAUSTED)

    def test_exception_always_returns_http_200(self):
        """AC-14: ApiResponse 永远返回 HTTP 200，code 承载业务错误。"""
        classes = [
            InputTooShortError,
            InputContentViolationError,
            QuizNotFoundError,
            DeepSeekRetryExhaustedError,
        ]
        for cls in classes:
            try:
                raise cls()
            except FishAIException as fe:
                assert fe.status_code == 200, f"{cls.__name__} status_code != 200"
                assert isinstance(fe.code, int) and fe.code != 0
            except Exception:
                pytest.fail(f"{cls.__name__} 不是 FishAIException 子类")
