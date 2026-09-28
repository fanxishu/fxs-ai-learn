import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import create_access_token  # noqa: E402


def _bearer(user_id: int = 1, openid: str = "oid_test") -> dict[str, str]:
    tok = create_access_token(user_id, openid)
    return {"Authorization": f"Bearer {tok}"}


class TestQuizGenerateTaskCreation:
    @pytest.mark.asyncio
    async def test_quiz_generate_returns_task_metadata(self, client):
        payload = {"user_input": "Python 基础入门语法与数据类型", "question_count": 5}
        with (
            patch("app.api.v1.routes.quiz.generate_task_id", return_value="qtask-test-1"),
            patch("app.api.v1.routes.quiz.schedule_quiz_generation_task"),
        ):
            resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["task_id"] == "qtask-test-1"
        assert body["data"]["status"] == "pending"
        assert body["data"]["poll_interval_seconds"] >= 1
        assert "result" not in body["data"]

    @pytest.mark.asyncio
    async def test_quiz_generate_missing_login_returns_2003(self, client):
        payload = {"user_input": "Python 基础入门语法与数据类型", "question_count": 5}
        resp = await client.post("/api/v1/quiz/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 2003


class TestQuizGenerateInputValidation:
    @pytest.mark.asyncio
    async def test_quiz_generate_empty_user_input_code_4000(self, client):
        payload = {"user_input": ""}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000
        assert body["data"] is None

    @pytest.mark.asyncio
    async def test_quiz_generate_short_input_abc_code_4000(self, client):
        payload = {"user_input": "abc"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000

    @pytest.mark.asyncio
    async def test_quiz_generate_count_6_over_max_code_4000(self, client):
        payload = {"user_input": "Python 基础入门足够长度的输入文本", "question_count": 6}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000

    @pytest.mark.asyncio
    async def test_quiz_generate_missing_user_input_code_4000(self, client):
        payload = {"question_count": 5}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000


class TestQuizGenerateCleanerAndFilter:
    @pytest.mark.asyncio
    async def test_quiz_generate_strips_html_and_still_creates_task(self, client):
        payload = {"user_input": "<p>Python <b>列表</b> 推导式<br/>用法示例</p>", "question_count": 5}
        with (
            patch("app.api.v1.routes.quiz.generate_task_id", return_value="qtask-html"),
            patch("app.api.v1.routes.quiz.schedule_quiz_generation_task"),
        ):
            resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["task_id"] == "qtask-html"

    @pytest.mark.asyncio
    async def test_quiz_generate_sensitive_赌博_code_4001(self, client):
        payload = {"user_input": "赌博秘籍分享 博彩网站推荐 必中秘诀"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4001
        assert "违规内容" in body["message"] or "敏感" in body["message"]

    @pytest.mark.asyncio
    async def test_quiz_generate_sensitive_hits_in_data(self, client):
        payload = {"user_input": "六合彩 时时彩 赌球技巧大公开"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4001
        assert isinstance(body["data"], dict)
        assert isinstance(body["data"].get("hits"), list)
        assert len(body["data"]["hits"]) >= 2


class TestQuizTaskStatus:
    @pytest.mark.asyncio
    async def test_get_task_status_running(self, client):
        with patch(
            "app.api.v1.routes.quiz.QuizTaskRepository.get_by_task_id_for_user",
            new=AsyncMock(
                return_value={
                    "task_id": "qtask-1",
                    "status": "running",
                    "result_json": None,
                    "error_message": None,
                }
            ),
        ):
            resp = await client.get("/api/v1/quiz/tasks/qtask-1", headers=_bearer(1))
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "running"
        assert body["data"]["result"] is None

    @pytest.mark.asyncio
    async def test_get_task_status_succeeded_returns_result(self, client):
        result_json = {
            "quiz_id": "quiz_1",
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
        with patch(
            "app.api.v1.routes.quiz.QuizTaskRepository.get_by_task_id_for_user",
            new=AsyncMock(
                return_value={
                    "task_id": "qtask-2",
                    "status": "succeeded",
                    "result_json": result_json,
                    "error_message": None,
                }
            ),
        ):
            resp = await client.get("/api/v1/quiz/tasks/qtask-2", headers=_bearer(1))
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "succeeded"
        assert body["data"]["result"]["quiz_id"] == "quiz_1"
        assert len(body["data"]["result"]["questions"]) == 3

    @pytest.mark.asyncio
    async def test_get_task_status_failed_returns_error_message(self, client):
        with patch(
            "app.api.v1.routes.quiz.QuizTaskRepository.get_by_task_id_for_user",
            new=AsyncMock(
                return_value={
                    "task_id": "qtask-3",
                    "status": "failed",
                    "result_json": None,
                    "error_message": "生成题目失败，请重试",
                }
            ),
        ):
            resp = await client.get("/api/v1/quiz/tasks/qtask-3", headers=_bearer(1))
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["status"] == "failed"
        assert body["data"]["error_message"] == "生成题目失败，请重试"

    @pytest.mark.asyncio
    async def test_get_task_status_other_user_returns_4001(self, client):
        with patch(
            "app.api.v1.routes.quiz.QuizTaskRepository.get_by_task_id_for_user",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get("/api/v1/quiz/tasks/qtask-404", headers=_bearer(2))
        body = resp.json()
        assert body["code"] == 4001
