from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.quiz import Question, QuizOption
from app.models.report import AnswerRecord, ScoreSummary


def _q(qid: str, qtype="single", kp: str | None = None, answer="A") -> Question:
    return Question(
        question_id=qid,
        question_type=qtype,
        stem=f"stem-{qid}",
        options=[
            QuizOption(key="A", text="A"),
            QuizOption(key="B", text="B"),
            QuizOption(key="C", text="C"),
            QuizOption(key="D", text="D"),
        ],
        answer=answer,
        knowledge_point=kp,
    )


def _judge(qid: str, kp: str | None = None, answer="对") -> Question:
    return Question(
        question_id=qid,
        question_type="judge",
        stem=f"judge-{qid}",
        options=[QuizOption(key="对", text="正确"), QuizOption(key="错", text="错误")],
        answer=answer,
        knowledge_point=kp,
    )


class TestScoringServiceInputValidation:
    def test_empty_records_raises(self):
        from app.services.scoring_service import ScoringService
        with pytest.raises(ValueError, match="records"):
            ScoringService.calc_score_summary(questions=[_q("q1")], records=[])

    def test_questions_must_not_be_empty(self):
        from app.services.scoring_service import ScoringService
        with pytest.raises(ValueError, match="questions"):
            ScoringService.calc_score_summary(
                questions=[],
                records=[AnswerRecord(question_id="q1", user_answer="A", is_correct=True)],
            )

    def test_duplicate_records_last_wins(self):
        from app.services.scoring_service import ScoringService
        questions = [_q("q1", kp="kp1")]
        records = [
            AnswerRecord(question_id="q1", user_answer="B", is_correct=False),
            AnswerRecord(question_id="q1", user_answer="A", is_correct=True),
        ]
        s = ScoringService.calc_score_summary(questions=questions, records=records)
        assert isinstance(s, ScoreSummary)
        assert s.total_count == 1
        assert s.correct_count == 1
        assert s.accuracy == 1.0
        assert s.score == 100


class TestScoringServiceAccuracyAndScore:
    def test_accuracy_3of5_rounds_to_60(self):
        from app.services.scoring_service import ScoringService
        questions = [_q(f"q{i}", kp="kp") for i in range(5)]
        records = [
            AnswerRecord(question_id="q0", user_answer="A", is_correct=True),
            AnswerRecord(question_id="q1", user_answer="A", is_correct=True),
            AnswerRecord(question_id="q2", user_answer="A", is_correct=True),
            AnswerRecord(question_id="q3", user_answer="B", is_correct=False),
            AnswerRecord(question_id="q4", user_answer="B", is_correct=False),
        ]
        s = ScoringService.calc_score_summary(questions, records)
        assert s.accuracy == 0.6
        assert s.score == 60

    def test_accuracy_half_rounds_up(self):
        from app.services.scoring_service import ScoringService
        questions = [_q(f"q{i}", kp="kp") for i in range(3)]
        records = [
            AnswerRecord(question_id="q0", user_answer="A", is_correct=True),
            AnswerRecord(question_id="q1", user_answer="B", is_correct=False),
            AnswerRecord(question_id="q2", user_answer="B", is_correct=False),
        ]
        s = ScoringService.calc_score_summary(questions, records)
        assert s.accuracy == pytest.approx(1 / 3)
        assert s.score == 33

    def test_perfect_score_100(self):
        from app.services.scoring_service import ScoringService
        qs = [_judge("j1", kp="k1", answer="对"), _q("s1", kp="k2", answer="A")]
        records = [
            AnswerRecord(question_id="j1", user_answer="对", is_correct=True),
            AnswerRecord(question_id="s1", user_answer="A", is_correct=True),
        ]
        s = ScoringService.calc_score_summary(qs, records)
        assert s.score == 100
        assert s.accuracy == 1.0

    def test_zero_score(self):
        from app.services.scoring_service import ScoringService
        qs = [_q("q1", kp="k1"), _judge("j1", kp="k2")]
        records = [
            AnswerRecord(question_id="q1", user_answer="B", is_correct=False),
            AnswerRecord(question_id="j1", user_answer="错", is_correct=False),
        ]
        s = ScoringService.calc_score_summary(qs, records)
        assert s.score == 0
        assert s.accuracy == 0.0


class TestScoringServiceKnowledgeMastery:
    def test_per_knowledge_aggregation_and_mastery_ordered_desc(self):
        from app.services.scoring_service import ScoringService
        qs = [
            _q("a1", kp="k_a", answer="A"),
            _q("a2", kp="k_a", answer="A"),
            _q("a3", kp="k_a", answer="B"),
            _judge("b1", kp="k_b", answer="对"),
            _judge("b2", kp="k_b", answer="对"),
        ]
        records = [
            AnswerRecord(question_id="a1", user_answer="A", is_correct=True),
            AnswerRecord(question_id="a2", user_answer="A", is_correct=True),
            AnswerRecord(question_id="a3", user_answer="B", is_correct=True),
            AnswerRecord(question_id="b1", user_answer="对", is_correct=True),
            AnswerRecord(question_id="b2", user_answer="错", is_correct=False),
        ]
        s = ScoringService.calc_score_summary(qs, records)
        mastery_map = {m.knowledge_point: m for m in s.per_knowledge}
        assert len(mastery_map) == 2
        assert mastery_map["k_a"].total_count == 3
        assert mastery_map["k_a"].correct_count == 3
        assert mastery_map["k_a"].mastery == 1.0
        assert mastery_map["k_b"].total_count == 2
        assert mastery_map["k_b"].correct_count == 1
        assert mastery_map["k_b"].mastery == 0.5
        mastery_sorted = [m.knowledge_point for m in s.per_knowledge]
        assert mastery_sorted.index("k_a") < mastery_sorted.index("k_b")

    def test_missing_record_is_treated_as_wrong(self):
        from app.services.scoring_service import ScoringService
        qs = [_q("q1", kp="k1"), _q("q2", kp="k2")]
        records = [AnswerRecord(question_id="q1", user_answer="A", is_correct=True)]
        s = ScoringService.calc_score_summary(qs, records)
        assert s.total_count == 2
        assert s.correct_count == 1
        assert s.score == 50
        m2 = next(m for m in s.per_knowledge if m.knowledge_point == "k2")
        assert m2.total_count == 1
        assert m2.correct_count == 0
        assert m2.mastery == 0.0
