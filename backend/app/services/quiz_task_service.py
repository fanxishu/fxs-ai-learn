from __future__ import annotations

import asyncio
import logging
import traceback
import uuid

from app.core.config import settings
from app.models.quiz import QuizGenerateRequest
from app.repositories import QuizSessionRepository, QuizTaskRepository
from app.services.quiz_chain import QuizChainService
from app.services.web_search_context_service import WebSearchContextService

logger = logging.getLogger(__name__)

_running_tasks: set[asyncio.Task] = set()


def generate_task_id() -> str:
    return f"qtask-{uuid.uuid4().hex[:16]}"


def schedule_quiz_generation_task(
    *,
    task_id: str,
    user_id: int,
    request: QuizGenerateRequest,
    cleaned_input: str,
) -> None:
    task = asyncio.create_task(
        _run_quiz_generation_task(
            task_id=task_id,
            user_id=user_id,
            request=request,
            cleaned_input=cleaned_input,
        )
    )
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)


async def _run_quiz_generation_task(
    *,
    task_id: str,
    user_id: int,
    request: QuizGenerateRequest,
    cleaned_input: str,
) -> None:
    try:
        await QuizTaskRepository.mark_running(task_id, user_id)
        knowledge_summary = await WebSearchContextService.generate_context(request.user_input)
        request = request.model_copy(update={"knowledge_summary": knowledge_summary or None})
        result = await asyncio.wait_for(
            QuizChainService.generate_quiz(request),
            timeout=settings.QUIZ_TASK_TIMEOUT_SECONDS,
        )
        result_dump = result.model_dump()
        await QuizSessionRepository.create(
            quiz_id=result.quiz_id,
            user_id=int(user_id),
            title=result.title,
            summary=None,
            user_input=cleaned_input,
            questions_json=result_dump.get("questions"),
        )
        await QuizTaskRepository.mark_succeeded(task_id, user_id, result_dump)
        logger.info("Quiz task succeeded task_id=%s user_id=%s", task_id, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Quiz task failed task_id=%s user_id=%s err=%s\nTB:\n%s",
            task_id,
            user_id,
            exc,
            traceback.format_exc(),
        )
        await QuizTaskRepository.mark_failed(
            task_id,
            user_id,
            "生成题目失败，请重试",
        )
