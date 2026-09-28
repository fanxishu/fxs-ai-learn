import logging as _logging

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.auth import get_current_user_id_optional
from app.core.config import settings
from app.core.exceptions import ErrorCode, NotLoggedInError, SensitiveContentError, ValidationError as AppValidationError
from app.models.common import ApiResponse, error_response, ok_response
from app.models.quiz import (
    QuizGenerateRequest,
    QuizGenerateTaskAccepted,
    QuizGenerateTaskStatusData,
    QuizGenerateResult,
)
from app.repositories import QuizTaskRepository
from app.services.quiz_task_service import generate_task_id, schedule_quiz_generation_task
from app.utils.content_filter import ContentFilter
from app.utils.text_cleaner import clean_user_input

router = APIRouter(prefix="/quiz", tags=["quiz"])

_content_filter = ContentFilter(file_path=settings.SENSITIVE_WORDS_FILE)
_log = _logging.getLogger(__name__)


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

    task_id = generate_task_id()
    try:
        await QuizTaskRepository.create(
            task_id=task_id,
            user_id=int(user_id),
            user_input=cleaned,
            question_count=int(req.question_count),
        )
        schedule_quiz_generation_task(
            task_id=task_id,
            user_id=int(user_id),
            request=req,
            cleaned_input=cleaned,
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("Quiz task create failed: %s", exc)
        return error_response(5001, "创建出题任务失败，请重试")

    accepted = QuizGenerateTaskAccepted(
        task_id=task_id,
        status="pending",
        poll_interval_seconds=settings.QUIZ_TASK_POLL_INTERVAL_SECONDS,
    )
    return ok_response(accepted.model_dump(), message="ok")


@router.get("/tasks/{task_id}")
async def get_quiz_task_status(
    task_id: str,
    user_id: int | None = Depends(get_current_user_id_optional),
) -> ApiResponse:
    if not user_id:
        return error_response(
            int(ErrorCode.NOT_LOGGED_IN),
            NotLoggedInError.message,
        )
    task = await QuizTaskRepository.get_by_task_id_for_user(task_id, int(user_id))
    if not task:
        return error_response(4001, "资源不存在")

    result = None
    if isinstance(task.get("result_json"), dict):
        try:
            result = QuizGenerateResult.model_validate(task["result_json"])
        except Exception:  # noqa: BLE001
            result = None
    data = QuizGenerateTaskStatusData(
        task_id=task["task_id"],
        status=task["status"],
        result=result,
        error_message=task.get("error_message"),
    )
    return ok_response(data.model_dump(), message="ok")
