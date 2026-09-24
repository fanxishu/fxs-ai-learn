import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "quiz_fixture_5q.json"

from app.models.quiz import QuizGenerateResult, QuizGenerateRequest
from app.models.report import (
    AnswerRecord,
    ReportGenerateRequest,
    ReportGenerateResult,
)


def _load_quiz() -> QuizGenerateResult:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return QuizGenerateResult.model_validate(raw)


@pytest.fixture
def standard_quiz() -> QuizGenerateResult:
    return _load_quiz()


@pytest.fixture
def records_3of5_60points(standard_quiz: QuizGenerateResult):
    qs = standard_quiz.questions
    return [
        AnswerRecord(question_id=qs[0].question_id, user_answer=qs[0].answer, is_correct=True, time_spent_ms=1200),
        AnswerRecord(question_id=qs[1].question_id, user_answer="A", is_correct=False, time_spent_ms=800),
        AnswerRecord(question_id=qs[2].question_id, user_answer=qs[2].answer, is_correct=True, time_spent_ms=500),
        AnswerRecord(question_id=qs[3].question_id, user_answer=["A", "B"], is_correct=False, time_spent_ms=3000),
        AnswerRecord(question_id=qs[4].question_id, user_answer=qs[4].answer, is_correct=True, time_spent_ms=400),
    ]


@pytest.fixture
def records_5of5_100points(standard_quiz: QuizGenerateResult):
    return [
        AnswerRecord(question_id=q.question_id, user_answer=q.answer, is_correct=True, time_spent_ms=1000)
        for q in standard_quiz.questions
    ]


@pytest.fixture
def records_0of5_0points(standard_quiz: QuizGenerateResult):
    wrong_map = {"A": "B", "B": "C", "C": "D", "D": "A", "对": "错", "错": "对"}
    out = []
    for q in standard_quiz.questions:
        if isinstance(q.answer, list):
            wrong = [k for k in ["A", "B", "C", "D"] if k not in q.answer][:2]
            out.append(AnswerRecord(question_id=q.question_id, user_answer=wrong, is_correct=False, time_spent_ms=500))
        else:
            wrong = wrong_map.get(q.answer, "A")
            out.append(AnswerRecord(question_id=q.question_id, user_answer=wrong, is_correct=False, time_spent_ms=500))
    return out


class TestReportChainShape:
    @pytest.mark.asyncio
    async def test_report_accuracy_3of5_equals_60(self, standard_quiz, records_3of5_60points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_3of5_60points,
        )
        result = await ReportChainService.generate_report(req)
        assert isinstance(result, ReportGenerateResult)
        assert result.accuracy == 60

    @pytest.mark.asyncio
    async def test_report_accuracy_5of5_equals_100(self, standard_quiz, records_5of5_100points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_5of5_100points,
        )
        result = await ReportChainService.generate_report(req)
        assert result.accuracy == 100
        assert "暂无" not in result.mastered_points

    @pytest.mark.asyncio
    async def test_report_accuracy_0of5_equals_0_weak_not_empty(self, standard_quiz, records_0of5_0points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_0of5_0points,
        )
        result = await ReportChainService.generate_report(req)
        assert result.accuracy == 0
        assert "暂无" not in result.weak_points
        assert result.mastered_points == ["暂无"]

    @pytest.mark.asyncio
    async def test_report_three_line_summary_len_3_and_non_empty(self, standard_quiz, records_3of5_60points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_3of5_60points,
        )
        result = await ReportChainService.generate_report(req)
        assert len(result.three_line_summary) == 3
        for line in result.three_line_summary:
            assert isinstance(line, str) and line.strip() != ""

    @pytest.mark.asyncio
    async def test_report_advice_and_share_quote_non_empty(self, standard_quiz, records_3of5_60points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_3of5_60points,
        )
        result = await ReportChainService.generate_report(req)
        assert isinstance(result.advice, str) and result.advice.strip() != ""
        assert len(result.advice) <= 2000
        assert isinstance(result.share_quote, str) and result.share_quote.strip() != ""
        assert len(result.share_quote) <= 500

    @pytest.mark.asyncio
    async def test_report_mastered_and_weak_always_non_empty_lists(self, standard_quiz, records_5of5_100points):
        from app.services.quiz_chain import ReportChainService

        req = ReportGenerateRequest(
            quiz_id=standard_quiz.quiz_id,
            quiz=standard_quiz,
            answer_records=records_5of5_100points,
        )
        result = await ReportChainService.generate_report(req)
        assert isinstance(result.mastered_points, list) and len(result.mastered_points) >= 1
        assert isinstance(result.weak_points, list) and len(result.weak_points) >= 1
