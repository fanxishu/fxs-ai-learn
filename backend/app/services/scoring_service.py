from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from app.models.quiz import Question
from app.models.report import (
    AnswerRecord,
    KnowledgePointMastery,
    ScoreSummary,
)

UNKNOWN_KNOWLEDGE_POINT = "未分类知识点"


class ScoringService:
    """纯算法服务：答题记录 → 分数摘要 + 知识点掌握度。"""

    @classmethod
    def calc_score_summary(
        cls,
        questions: Sequence[Question],
        records: Sequence[AnswerRecord],
    ) -> ScoreSummary:
        if not questions:
            raise ValueError("questions 不能为空")
        if not records:
            raise ValueError("records 不能为空")

        total = len(questions)
        qid_to_q = {cls._qid(q): q for q in questions}
        last_records: dict[str, AnswerRecord] = {}
        for r in records:
            last_records[r.question_id] = r

        correct_count = 0
        per_kp_correct: dict[str, int] = defaultdict(int)
        per_kp_total: dict[str, int] = defaultdict(int)

        for q in questions:
            qid = cls._qid(q)
            kp = q.knowledge_point or UNKNOWN_KNOWLEDGE_POINT
            per_kp_total[kp] += 1
            record = last_records.get(qid)
            is_correct = bool(record and record.is_correct)
            if is_correct:
                correct_count += 1
                per_kp_correct[kp] += 1

        accuracy = (correct_count / total) if total > 0 else 0.0
        score = int(round(accuracy * 100))
        score = max(0, min(100, score))

        per_knowledge = [
            KnowledgePointMastery(
                knowledge_point=kp,
                correct_count=per_kp_correct.get(kp, 0),
                total_count=total_count,
                mastery=(per_kp_correct.get(kp, 0) / total_count),
            )
            for kp, total_count in per_kp_total.items()
        ]
        per_knowledge.sort(
            key=lambda m: (-m.mastery, m.total_count, m.knowledge_point)
        )

        return ScoreSummary(
            total_count=total,
            correct_count=correct_count,
            accuracy=accuracy,
            score=score,
            per_knowledge=per_knowledge,
        )

    @classmethod
    def split_mastery_vs_weak(
        cls,
        per_knowledge: Iterable[KnowledgePointMastery],
        mastery_threshold: float = 0.8,
        weak_threshold: float = 0.6,
    ) -> tuple[list[str], list[str]]:
        mastered: list[str] = []
        weak: list[str] = []
        for m in per_knowledge:
            if m.mastery >= mastery_threshold:
                mastered.append(m.knowledge_point)
            elif m.mastery <= weak_threshold:
                weak.append(m.knowledge_point)
        return mastered, weak

    @staticmethod
    def _qid(q: Question) -> str:
        return q.id if isinstance(getattr(q, "id", None), str) and q.id else (q.question_id or f"q_{hash(q.stem)}")
