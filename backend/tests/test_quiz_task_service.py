import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.quiz import QuizGenerateRequest, QuizGenerateResult  # noqa: E402
from app.services.quiz_task_service import _run_quiz_generation_task  # noqa: E402


def _result() -> QuizGenerateResult:
    return QuizGenerateResult.model_validate(
        {
            "quiz_id": "quiz-123",
            "title": "测试题目",
            "questions": [
                {
                    "question_id": "q1",
                    "stem": "1+1=?",
                    "question_type": "single",
                    "options": [{"key": "A", "text": "2"}, {"key": "B", "text": "3"}],
                    "answer": "A",
                    "knowledge_point": "加法",
                    "explanation": "1+1=2",
                },
                {
                    "question_id": "q2",
                    "stem": "Python 是解释型语言",
                    "question_type": "judge",
                    "options": [{"key": "T", "text": "正确"}, {"key": "F", "text": "错误"}],
                    "answer": "T",
                    "knowledge_point": "Python",
                    "explanation": "Python 通常被视为解释型语言。",
                },
                {
                    "question_id": "q3",
                    "stem": "哪些是 Python 集合类型？",
                    "question_type": "multiple",
                    "options": [{"key": "A", "text": "set"}, {"key": "B", "text": "dict"}],
                    "answer": ["A", "B"],
                    "knowledge_point": "集合",
                    "explanation": "set 和 dict 都与集合概念相关。",
                },
            ],
        }
    )


@pytest.mark.asyncio
async def test_quiz_task_runner_success_persists_and_marks_succeeded():
    captured = {}

    async def _fake_generate_quiz(request):
        captured["knowledge_summary"] = request.knowledge_summary
        return _result()

    with (
        patch("app.services.quiz_task_service.QuizTaskRepository.mark_running", new=AsyncMock()),
        patch("app.services.quiz_task_service.WebSearchContextService.generate_context", new=AsyncMock(return_value="联网知识摘要")),
        patch("app.services.quiz_task_service.QuizChainService.generate_quiz", new=AsyncMock(side_effect=_fake_generate_quiz)),
        patch("app.services.quiz_task_service.QuizSessionRepository.create", new=AsyncMock()),
        patch("app.services.quiz_task_service.QuizTaskRepository.mark_succeeded", new=AsyncMock()) as mark_succeeded,
    ):
        await _run_quiz_generation_task(
            task_id="qtask-1",
            user_id=1,
            request=QuizGenerateRequest(user_input="Harness Engineering", question_count=3),
            cleaned_input="Harness Engineering",
        )

    assert captured["knowledge_summary"] == "联网知识摘要"
    mark_succeeded.assert_awaited_once()
    assert mark_succeeded.await_args.args[2]["quiz_id"] == "quiz-123"


@pytest.mark.asyncio
async def test_quiz_task_runner_failure_marks_failed():
    with (
        patch("app.services.quiz_task_service.QuizTaskRepository.mark_running", new=AsyncMock()),
        patch("app.services.quiz_task_service.WebSearchContextService.generate_context", new=AsyncMock(return_value="")),
        patch("app.services.quiz_task_service.QuizChainService.generate_quiz", new=AsyncMock(side_effect=RuntimeError("llm boom"))),
        patch("app.services.quiz_task_service.QuizTaskRepository.mark_failed", new=AsyncMock()) as mark_failed,
    ):
        await _run_quiz_generation_task(
            task_id="qtask-2",
            user_id=1,
            request=QuizGenerateRequest(user_input="Harness Engineering", question_count=3),
            cleaned_input="Harness Engineering",
        )

    mark_failed.assert_awaited_once()
    assert mark_failed.await_args.args[0] == "qtask-2"
