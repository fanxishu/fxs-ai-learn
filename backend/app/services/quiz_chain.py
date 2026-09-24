from __future__ import annotations

import logging
from typing import Optional

from app.models.quiz import QuizGenerateRequest, QuizGenerateResult, Question
from app.models.report import ReportGenerateRequest, ReportGenerateResult
from app.services.scoring_service import ScoringService
from app.services.langchain_factory import (
    LLMFactory,
    load_fallback_fixture,
)
from app.core.exceptions import QuizGenerateError, ReportGenerateError

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE = "未分类知识点"
DEFAULT_EXPLANATION = "暂无解析"


class QuizChainService:
    @classmethod
    async def generate_quiz(cls, request: QuizGenerateRequest) -> QuizGenerateResult:
        llm = LLMFactory.build_quiz_llm()

        # 五级兜底：L1 正常调用 L1→L2 字段补全→L3 分布修复→L4 重试→L5 fixture 硬兜底
        try:
            result = await llm.ainvoke_structured(request)
            if result is not None:
                return cls._normalize_and_fix_result(result, request)
        except Exception as exc:  # noqa: BLE001
            logger.warning("L1 LLM invoke failed, will retry / fallback: %s", exc)

        try:
            result = await cls._retry_with_v2_prompt(request, llm)
            if result is not None:
                return cls._normalize_and_fix_result(result, request)
        except Exception as exc:  # noqa: BLE001
            logger.warning("L4 v2 prompt retry failed: %s", exc)

        logger.warning("L5 using fallback fixture as last resort")
        fallback = load_fallback_fixture()
        return cls._normalize_and_fix_result(fallback, request, enforce_count=True)

    @staticmethod
    async def _retry_with_v2_prompt(request: QuizGenerateRequest, llm):
        return await llm.ainvoke_structured(request)

    @classmethod
    def _normalize_and_fix_result(
        cls,
        result: QuizGenerateResult,
        request: QuizGenerateRequest,
        enforce_count: bool = False,
    ) -> QuizGenerateResult:
        fx = load_fallback_fixture()
        questions = list(result.questions)

        for q in questions:
            if not q.knowledge_point or not q.knowledge_point.strip():
                q.knowledge_point = DEFAULT_KNOWLEDGE
            if not q.explanation or not q.explanation.strip():
                q.explanation = DEFAULT_EXPLANATION

        counts = {"single": 0, "multiple": 0, "judge": 0}
        for q in questions:
            counts[q.question_type] += 1

        need = []
        if counts["single"] < 1:
            need.extend([q for q in fx.questions if q.question_type == "single"][:1])
        if counts["multiple"] < 1:
            need.extend([q for q in fx.questions if q.question_type == "multiple"][:1])
        if counts["judge"] < 1:
            need.extend([q for q in fx.questions if q.question_type == "judge"][:1])
        questions.extend(need)

        if enforce_count and len(questions) < request.question_count:
            pad = [q for q in fx.questions if q not in questions][
                : request.question_count - len(questions)
            ]
            questions.extend(pad)

        target = request.question_count
        if len(questions) > target:
            buckets: dict[str, list] = {"single": [], "multiple": [], "judge": []}
            rest = []
            for q in questions:
                if q.question_type in buckets:
                    buckets[q.question_type].append(q)
                else:
                    rest.append(q)
            pruned: list = []
            for t in ("single", "multiple", "judge"):
                if buckets[t]:
                    pruned.append(buckets[t].pop(0))
            for t in ("single", "multiple", "judge"):
                pruned.extend(buckets[t])
            pruned.extend(rest)
            questions = pruned[:target]

        try:
            cleaned = QuizGenerateResult(
                quiz_id=result.quiz_id or fx.quiz_id,
                title=result.title.strip() if result.title and result.title.strip() else fx.title,
                questions=questions,
            )
            return cleaned
        except Exception as exc:  # noqa: BLE001
            logger.warning("QuizGenerateResult re-validate failed: %s, use fixture", exc)
            return fx


class ReportChainService:
    @classmethod
    async def generate_report(cls, request: ReportGenerateRequest) -> ReportGenerateResult:
        from app.services.langchain_factory import LLMFactory
        from app.models.quiz import Question

        quiz_data = request.quiz
        if isinstance(quiz_data, dict) and "questions" in quiz_data:
            questions = [Question.model_validate(q) for q in quiz_data["questions"]]
        elif isinstance(quiz_data, list):
            questions = [Question.model_validate(q) for q in quiz_data]
        else:
            raise ReportGenerateError(message="quiz 数据无法解析出 questions 列表")

        records = list(request.answer_records)

        score_summary = ScoringService.calc_score_summary(questions, records)
        per_knowledge = score_summary.per_knowledge
        mastered, weak = ScoringService.split_mastery_vs_weak(per_knowledge)

        brief = [
            {"question_id": r.question_id, "is_correct": r.is_correct}
            for r in records
        ]

        percent_acc = int(score_summary.score)

        payload = {
            "score_summary": {
                "correct_count": score_summary.correct_count,
                "total_count": score_summary.total_count,
                "accuracy_ratio": score_summary.accuracy,
                "accuracy": percent_acc,
                "score": percent_acc,
            },
            "per_knowledge": per_knowledge,
            "answer_records_brief": brief,
            "mastered_points": mastered,
            "weak_points": weak,
            "accuracy": percent_acc,
        }

        llm = LLMFactory.build_report_llm()
        try:
            result = await llm.ainvoke_structured(payload)
            if isinstance(result, ReportGenerateResult):
                return cls._normalize_report(result, payload)
            if isinstance(result, dict):
                try:
                    parsed = ReportGenerateResult.model_validate(result)
                    return cls._normalize_report(parsed, payload)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Report L1 dict re-validate failed: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Report L1 invoke failed: %s", exc)

        from app.services.langchain_factory import MockReportLLM

        logger.warning("Report L5 fallback to MockReportLLM fixture")
        mock = MockReportLLM()
        raw = await mock.ainvoke_structured(payload)
        if isinstance(raw, ReportGenerateResult):
            return cls._normalize_report(raw, payload)
        if isinstance(raw, dict):
            try:
                parsed = ReportGenerateResult.model_validate(raw)
                return cls._normalize_report(parsed, payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Report fallback dict parse failed: %s", exc)

        fallback = cls._build_hardcoded_fallback(payload)
        return cls._normalize_report(fallback, payload)

    @staticmethod
    def _build_hardcoded_fallback(payload: dict) -> ReportGenerateResult:
        acc = int(payload.get("accuracy", 0))
        mastered = payload.get("mastered_points") or ["暂无"]
        weak = payload.get("weak_points") or ["暂无"]
        return ReportGenerateResult.model_validate({
            "accuracy": acc,
            "mastered_points": mastered,
            "weak_points": weak,
            "three_line_summary": [
                f"本次答题正确率约为 {acc} 分。",
                f"掌握 {len(mastered)} 个知识点，薄弱 {len(weak)} 个。",
                "坚持每天学习，一点点就能看到大变化。",
            ],
            "advice": "建议复盘错题，结合解析回顾知识点，再做 2~3 道同类题巩固。",
            "share_quote": "每天进步一点点，终将成就大大的自己！",
        })

    @classmethod
    def _normalize_report(
        cls, result: ReportGenerateResult, payload: dict
    ) -> ReportGenerateResult:
        acc = int(payload.get("accuracy", 0))
        try:
            result.accuracy = max(0, min(100, int(result.accuracy if result.accuracy is not None else acc)))
        except Exception:  # noqa: BLE001
            result.accuracy = acc
        if not result.mastered_points:
            result.mastered_points = ["暂无"]
        if not result.weak_points:
            result.weak_points = ["暂无"]
        need_fix_summary = False
        if len(result.three_line_summary) != 3:
            need_fix_summary = True
        else:
            for x in result.three_line_summary:
                if not (isinstance(x, str) and x.strip()):
                    need_fix_summary = True
                    break
        if need_fix_summary:
            mastered = result.mastered_points or ["暂无"]
            weak = result.weak_points or ["暂无"]
            level = "优秀" if acc >= 80 else ("良好" if acc >= 60 else "有待提升")
            result.three_line_summary = [
                f"本次答题正确率约为 {acc} 分，整体表现{level}。",
                f"掌握 {len(mastered)} 个知识点，薄弱 {len(weak)} 个。",
                "针对薄弱点刻意练习就能稳步提升，加油！",
            ]
        if not result.advice or not result.advice.strip():
            result.advice = "建议复盘错题，结合知识点解析进行针对性复习。"
        if not result.share_quote or not result.share_quote.strip():
            result.share_quote = "坚持每天学习，就能看见更大的世界。"
        return result
