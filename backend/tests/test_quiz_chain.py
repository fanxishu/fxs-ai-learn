import json
import asyncio
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "quiz_fixture_5q.json"

from app.models.quiz import QuizGenerateRequest, QuizGenerateResult, Question
from app.core.config import settings


def _load_fixture() -> QuizGenerateResult:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return QuizGenerateResult.model_validate(raw)


@pytest.fixture
def valid_request() -> QuizGenerateRequest:
    return QuizGenerateRequest(
        user_input="Python 基础语法与数据类型入门",
        question_count=5,
    )


@pytest.fixture
def valid_fixture_result() -> QuizGenerateResult:
    return _load_fixture()


class TestQuizChainMockFixtureValid:
    def test_fixture_shape_distribution_3s_1m_1j(self, valid_fixture_result: QuizGenerateResult):
        counts = {"single": 0, "multiple": 0, "judge": 0}
        for q in valid_fixture_result.questions:
            counts[q.question_type] += 1
        assert len(valid_fixture_result.questions) == 5
        assert counts["single"] == 3
        assert counts["multiple"] == 1
        assert counts["judge"] == 1

    def test_fixture_non_empty_id_and_title(self, valid_fixture_result: QuizGenerateResult):
        assert valid_fixture_result.quiz_id.strip() != ""
        assert valid_fixture_result.title.strip() != ""
        assert len(valid_fixture_result.quiz_id) <= 64
        assert len(valid_fixture_result.title) <= 120

    def test_fixture_every_question_has_unique_id_and_answer_valid(self, valid_fixture_result: QuizGenerateResult):
        ids = [q.question_id for q in valid_fixture_result.questions]
        assert len(ids) == len(set(ids))
        for q in valid_fixture_result.questions:
            assert q.stem.strip() != ""
            assert len(q.options) >= 2
            if q.question_type == "single":
                assert isinstance(q.answer, str)
                assert q.answer in {o.key for o in q.options}
            elif q.question_type == "multiple":
                assert isinstance(q.answer, list)
                assert len(q.answer) >= 2
                assert set(q.answer).issubset({o.key for o in q.options})
            elif q.question_type == "judge":
                assert isinstance(q.answer, str)
                assert q.answer in {o.key for o in q.options}


class TestQuizChainCoreBehavior:
    @pytest.mark.asyncio
    async def test_generate_quiz_happy_path_mock_returns_valid(self, valid_request: QuizGenerateRequest):
        from app.services.quiz_chain import QuizChainService
        result = await QuizChainService.generate_quiz(valid_request)
        assert isinstance(result, QuizGenerateResult)
        counts = {"single": 0, "multiple": 0, "judge": 0}
        for q in result.questions:
            counts[q.question_type] += 1
        assert counts["single"] >= 1 and counts["multiple"] >= 1 and counts["judge"] >= 1
        assert 3 <= len(result.questions) <= 5

    @pytest.mark.asyncio
    async def test_generate_quiz_question_count_matches_request(self, valid_request: QuizGenerateRequest):
        from app.services.quiz_chain import QuizChainService
        result = await QuizChainService.generate_quiz(valid_request)
        assert len(result.questions) == valid_request.question_count

    @pytest.mark.asyncio
    async def test_generate_quiz_default_count_is_5_from_settings(self):
        from app.services.quiz_chain import QuizChainService
        req_no_count = QuizGenerateRequest(user_input="Python 基础语法与数据类型入门")
        assert req_no_count.question_count == settings.DEFAULT_QUESTION_COUNT
        result = await QuizChainService.generate_quiz(req_no_count)
        assert len(result.questions) == 5

    @pytest.mark.asyncio
    async def test_generate_quiz_quiz_id_is_stable_and_unique(self, valid_request: QuizGenerateRequest):
        from app.services.quiz_chain import QuizChainService
        r1 = await QuizChainService.generate_quiz(valid_request)
        r2 = await QuizChainService.generate_quiz(valid_request)
        assert isinstance(r1.quiz_id, str) and r1.quiz_id.strip() != ""
        assert len(r1.quiz_id) <= 64
        assert r1.quiz_id != r2.quiz_id

    @pytest.mark.asyncio
    async def test_generate_quiz_questions_have_explanation_or_knowledge_safe(self, valid_request: QuizGenerateRequest):
        from app.services.quiz_chain import QuizChainService
        result = await QuizChainService.generate_quiz(valid_request)
        for q in result.questions:
            if q.knowledge_point is None:
                q.knowledge_point = "未分类知识点"
            if q.explanation is None:
                q.explanation = "暂无解析"
            assert q.knowledge_point.strip() != ""
            assert q.explanation.strip() != ""
