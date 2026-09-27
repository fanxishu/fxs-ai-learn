import logging as _logging

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.auth import get_current_user_id_optional
from app.core.config import settings
from app.core.exceptions import ErrorCode, NotLoggedInError, SensitiveContentError, ValidationError as AppValidationError
from app.models.common import ApiResponse, error_response, ok_response
from app.models.quiz import QuizGenerateRequest
from app.repositories import QuizSessionRepository
from app.services.quiz_chain import QuizChainService
from app.utils.content_filter import ContentFilter
from app.utils.text_cleaner import clean_user_input

router = APIRouter(prefix="/quiz", tags=["quiz"])

_content_filter = ContentFilter(file_path=settings.SENSITIVE_WORDS_FILE)
_log = _logging.getLogger(__name__)


async def _persist_quiz_if_logged_in(
    user_id: int | None,
    quiz_id: str,
    title: str,
    user_input: str,
    questions_dump,
) -> None:
    if not user_id:
        _log.info("Persist quiz skipped (anonymous) quiz_id=%s", quiz_id)
        return
    try:
        await QuizSessionRepository.create(
            quiz_id=quiz_id,
            user_id=int(user_id),
            title=title,
            summary=None,
            user_input=user_input,
            questions_json=questions_dump,
        )
        _log.info("Persist quiz OK quiz_id=%s user_id=%s", quiz_id, user_id)
    except Exception as exc:  # noqa: BLE001
        import traceback as _tb
        _log.error(
            "Persist quiz FAILED (non-fatal) quiz_id=%s user_id=%s err=%s\nTB:\n%s",
            quiz_id, user_id, exc, _tb.format_exc(),
        )


@router.post("/generate")
async def generate_quiz(
    request: Request,
    user_id: int | None = Depends(get_current_user_id_optional),
) -> ApiResponse:
    if not user_id:
        return error_response(
            int(ErrorCode.NOT_LOGGED_IN),
            NotLoggedInError.message,
        )
    try:
        raw = await request.json()
    except Exception:
        return error_response(4000, "请求体必须是合法的 JSON")

    if not isinstance(raw, dict):
        return error_response(4000, "请求体必须是 JSON 对象")

    raw_user_input = raw.get("user_input") or ""
    cleaned = clean_user_input(
        raw_user_input,
        max_len=settings.USER_INPUT_MAX_LEN,
    )

    question_count = raw.get("question_count", settings.DEFAULT_QUESTION_COUNT)

    try:
        req = QuizGenerateRequest(
            user_input=cleaned,
            question_count=question_count,
        )
    except (ValidationError, AppValidationError, RequestValidationError) as exc:
        msg = "参数校验失败"
        try:
            if isinstance(exc, ValidationError):
                first_err = exc.errors()[0] if exc.errors() else {}
                loc = ".".join(str(x) for x in first_err.get("loc", [])) or "input"
                msg = f"参数 {loc} 不合法"
        except Exception:  # noqa: BLE001
            pass
        return error_response(4000, msg)

    if len(cleaned) < settings.USER_INPUT_MIN_LEN:
        return error_response(
            4000,
            f"输入内容至少需要 {settings.USER_INPUT_MIN_LEN} 个字符",
        )

    hits = _content_filter.find_all(cleaned)
    if hits:
        return ApiResponse(
            code=4001,
            message="输入包含违规内容，请修改后重试",
            data={"hits": hits},
        )

    try:
        result = await QuizChainService.generate_quiz(req)
    except Exception as exc:  # noqa: BLE001
        _log.warning("Quiz generate chain failed: %s", exc)
        return error_response(5001, "生成题目失败，请重试")

    result_dump = result.model_dump()
    await _persist_quiz_if_logged_in(
        user_id=user_id,
        quiz_id=result.quiz_id,
        title=result.title,
        user_input=cleaned,
        questions_dump=result_dump.get("questions"),
    )

    return ok_response(result_dump, message="ok")
