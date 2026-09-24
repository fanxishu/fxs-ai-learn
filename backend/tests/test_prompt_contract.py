from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pydantic import ValidationError

from app.models.quiz import (
    Question,
    QuizGenerateRequest,
    QuizGenerateResult,
    QuizOption,
)
from app.models.report import ReportGenerateResult





def _opts(keys: list[str], texts: list[str] | None = None) -> list[QuizOption]:
    texts = texts or [f"选项{k}" for k in keys]
    return [QuizOption(key=k, text=t) for k, t in zip(keys, texts)]


class TestQuizRequestContract:
    def test_request_ok_default_count(self):
        r = QuizGenerateRequest(user_input="12345")
        assert r.question_count == 5
        assert len(r.user_input) == 5

    def test_request_too_short_rejected(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="x")

    def test_request_too_long_rejected(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="x" * 501)

    def test_request_count_bounds(self):
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="abcde", question_count=2)
        with pytest.raises(ValidationError):
            QuizGenerateRequest(user_input="abcde", question_count=6)


class TestQuestionContract:
    def test_judge_must_have_two_options(self):
        with pytest.raises(ValidationError) as exc:
            Question(
                question_id="q1",
                question_type="judge",
                stem="勾股定理对吗？",
                options=_opts(["对"]),
                answer="对",
            )
        msg = str(exc.value)
        assert (
            "恰好有 2 个选项" in msg
            or "2 个选项" in msg
            or "at least 2 items" in msg
            or "至少 2" in msg
        )

    def test_judge_answer_must_match_option_keys(self):
        with pytest.raises(ValidationError):
            Question(
                question_id="q2",
                question_type="judge",
                stem="对吗？",
                options=_opts(["对", "错"]),
                answer="A",
            )

    def test_multiple_answer_must_be_array_at_least_two(self):
        with pytest.raises(ValidationError) as exc:
            Question(
                question_id="q3",
                question_type="multiple",
                stem="以下哪些是水果？",
                options=_opts(["A", "B", "C", "D"]),
                answer="A",
            )
        assert "长度 >=2" in str(exc.value) or "长度 >=" in str(exc.value)

    def test_multiple_answer_must_be_subset_of_options(self):
        with pytest.raises(ValidationError):
            Question(
                question_id="q4",
                question_type="multiple",
                stem="哪些是素数？",
                options=_opts(["A", "B", "C", "D"]),
                answer=["A", "E"],
            )

    def test_single_answer_must_be_string_in_options(self):
        with pytest.raises(ValidationError):
            Question(
                question_id="q5",
                question_type="single",
                stem="首都？",
                options=_opts(["A", "B", "C", "D"]),
                answer=["A"],
            )

    def test_option_keys_must_be_unique(self):
        with pytest.raises(ValidationError) as exc:
            Question(
                question_id="q6",
                question_type="single",
                stem="x",
                options=[
                    QuizOption(key="A", text="x"),
                    QuizOption(key="A", text="y"),
                ],
                answer="A",
            )
        assert "唯一" in str(exc.value)

    def test_good_judge_question_passes(self):
        q = Question(
            question_id="qok",
            question_type="judge",
            stem="Python 是动态语言。",
            options=_opts(["对", "错"]),
            answer="对",
            knowledge_point="语言特性",
            explanation="对，Python 是解释型动态语言。",
            difficulty=2,
        )
        assert q.model_dump()["question_id"] == "qok"
        assert q.knowledge_point == "语言特性"


class TestQuizGenerateResultContract:
    def _make_question(self, qid: str, qtype, answer, opts=None):
        if qtype == "judge":
            opts = opts or _opts(["对", "错"])
        else:
            opts = opts or _opts(["A", "B", "C", "D"])
        return Question(
            question_id=qid,
            question_type=qtype,
            stem=f"题目 {qid}",
            options=opts,
            answer=answer,
        )

    def test_distribution_requires_all_three_types(self):
        with pytest.raises(ValidationError) as exc:
            QuizGenerateResult(
                quiz_id="quiz1",
                title="测试卷",
                questions=[
                    self._make_question("s1", "single", "A"),
                    self._make_question("s2", "single", "B"),
                    self._make_question("s3", "single", "C"),
                    self._make_question("s4", "single", "D"),
                    self._make_question("s5", "single", "A"),
                ],
            )
        assert "题型分布" in str(exc.value)

    def test_valid_distribution_passes(self):
        result = QuizGenerateResult(
            quiz_id="quiz2",
            title="混合卷",
            questions=[
                self._make_question("s1", "single", "A"),
                self._make_question("s2", "single", "B"),
                self._make_question("s3", "single", "C"),
                self._make_question("m1", "multiple", ["A", "B"]),
                self._make_question("j1", "judge", "对"),
            ],
        )
        assert len(result.questions) == 5
        types = sorted(q.question_type for q in result.questions)
        assert types == ["judge", "multiple", "single", "single", "single"]


class TestReportGenerateResultContract:
    def _valid_payload(self, **overrides):
        base = {
            "accuracy": 80,
            "mastered_points": ["基础概念"],
            "weak_points": ["细节辨析"],
            "three_line_summary": [
                "你答对了 4/5 题。",
                "继续加油，薄弱点要多练。",
                "建议 24 小时后重闯。",
            ],
            "advice": "间隔重复 + 错题本。",
            "share_quote": "鱼皮 AI 闯关，正确率 80%，继续冲！",
        }
        base.update(overrides)
        return base

    def test_three_line_summary_must_be_len_3(self):
        with pytest.raises(ValidationError) as exc:
            ReportGenerateResult(
                **self._valid_payload(three_line_summary=["a", "b"])
            )
        msg = str(exc.value)
        assert "长度必须为 3" in msg or "at least 3 items" in msg or "至少 3" in msg

    def test_three_line_summary_empty_item_rejected(self):
        with pytest.raises(ValidationError):
            ReportGenerateResult(
                **self._valid_payload(
                    three_line_summary=["a", "  ", "c"]
                )
            )

    def test_mandatory_fields_non_empty(self):
        with pytest.raises(ValidationError):
            ReportGenerateResult(**self._valid_payload(advice=""))
        with pytest.raises(ValidationError):
            ReportGenerateResult(**self._valid_payload(share_quote=""))

    def test_accuracy_must_be_between_0_and_100(self):
        with pytest.raises(ValidationError):
            ReportGenerateResult(**self._valid_payload(accuracy=-1))
        with pytest.raises(ValidationError):
            ReportGenerateResult(**self._valid_payload(accuracy=101))

    def test_mastered_or_weak_empty_uses_sentinel(self):
        r = ReportGenerateResult(
            **self._valid_payload(mastered_points=[], weak_points=[])
        )
        assert r.mastered_points == ["暂无"]
        assert r.weak_points == ["暂无"]

    def test_valid_report_passes(self):
        r = ReportGenerateResult(**self._valid_payload())
        dumped = r.model_dump()
        assert dumped["accuracy"] == 80
        assert len(dumped["three_line_summary"]) == 3
        assert all(isinstance(x, str) and x for x in dumped["three_line_summary"])
