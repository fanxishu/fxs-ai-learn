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
from app.core.exceptions import (
    QuizGenerateError,
    ReportGenerateError,
    InputContentViolationError,
    OutputContentViolationError,
    InputTooShortError,
    InputTooLongError,
)
from app.utils.content_filter import DFASensitiveWordFilter
from app.utils.text_cleaner import clean_user_input

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE = "未分类知识点"
DEFAULT_EXPLANATION = "暂无解析"
_INPUT_FILTER = DFASensitiveWordFilter()
_OUTPUT_FILTER = DFASensitiveWordFilter()
_MIN_USER_INPUT_LEN = 2
_MAX_USER_INPUT_LEN = 500


class QuizChainService:
    @classmethod
    async def generate_quiz(cls, request: QuizGenerateRequest) -> QuizGenerateResult:
        # 第一层：参数长度 + 清洗（不依赖前端）
        raw_input = request.user_input or ""
        if not isinstance(raw_input, str):
            raw_input = str(raw_input)
        cleaned_input = clean_user_input(raw_input, max_len=_MAX_USER_INPUT_LEN)
        if len(cleaned_input) < _MIN_USER_INPUT_LEN:
            raise InputTooShortError()
        if len(raw_input.strip()) > _MAX_USER_INPUT_LEN:
            raise InputTooLongError()

        # 第二层：输入 DFA 敏感词扫描
        hits_in = _INPUT_FILTER.find_all(cleaned_input)
        if hits_in:
            logger.warning("Quiz generate input hit sensitive words: %s", hits_in)
            raise InputContentViolationError()

        llm = LLMFactory.build_quiz_llm()

        # 五级兜底：L1 正常调用 L1→L2 字段补全→L3 分布修复→L4 重试→L5 fixture 硬兜底
        try:
            result = await llm.ainvoke_structured(request)
            if result is not None:
                fixed = cls._normalize_and_fix_result(result, request)
                cls._scan_output_violation(fixed)
                return fixed
        except (OutputContentViolationError, InputContentViolationError, InputTooShortError, InputTooLongError):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("L1 LLM invoke failed, will retry / fallback: %s", exc)

        try:
            result = await cls._retry_with_v2_prompt(request, llm)
            if result is not None:
                fixed = cls._normalize_and_fix_result(result, request)
                cls._scan_output_violation(fixed)
                return fixed
        except (OutputContentViolationError, InputContentViolationError, InputTooShortError, InputTooLongError):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("L4 v2 prompt retry failed: %s", exc)

        logger.warning("L5 using fallback fixture as last resort")
        fallback = load_fallback_fixture()
        fixed = cls._normalize_and_fix_result(fallback, request, enforce_count=True)
        # fixture 是硬编码可信任，跳过 Output 扫描，保证 L5 永远成功
        return fixed

    @staticmethod
    def _scan_output_violation(result: QuizGenerateResult) -> None:
        """第三层：LLM 输出 DFA 二次扫描。命中直接抛错，不泄漏敏感内容。"""
        pieces: list[str] = []
        if result.title:
            pieces.append(result.title)
        for q in result.questions:
            if q.stem:
                pieces.append(q.stem)
            if q.explanation:
                pieces.append(q.explanation)
            if q.options:
                for o in q.options:
                    if o and getattr(o, "text", None):
                        pieces.append(o.text)
        haystack = "\n".join(pieces)
        hits = _OUTPUT_FILTER.find_all(haystack)
        if hits:
            logger.warning("Quiz generate output hit sensitive words: %s", hits)
            raise OutputContentViolationError()

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

        # Report 入口同样 DFA：扫描 answer_records 自定义字段 / mastered_points 用户自定义上传部分
        pieces: list[str] = []
        for r in request.answer_records or []:
            user_answer = getattr(r, "user_answer", None) or []
            if isinstance(user_answer, str):
                ans_iter: list[str] = [user_answer] if user_answer else []
            elif isinstance(user_answer, list):
                ans_iter = [a for a in user_answer if isinstance(a, str) and a]
            else:
                ans_iter = []
            for ans in ans_iter:
                pieces.append(ans)
            if getattr(r, "user_note", None) and isinstance(getattr(r, "user_note", None), str):
                pieces.append(getattr(r, "user_note"))
        hits_report_in = _INPUT_FILTER.find_all("\n".join(pieces))
        if hits_report_in:
            logger.warning("Report generate input hit sensitive words: %s", hits_report_in)
            raise InputContentViolationError()

        quiz_data = request.quiz

        def _normalize_question_dict(q_obj):
            """把前端自定义题目字段名转换成后端 Question.schema 必填的字段。
            目前差异只有：前端写的是 question 字段，后端 schema 要求是 stem。
            由于 Question.extra = allow，多余字段可以原样保留，仅补缺失 stem。
            """
            if not isinstance(q_obj, dict):
                return q_obj
            out = {k: v for k, v in q_obj.items() if not (isinstance(k, str) and len(k) > 0 and k[0] == "_")}
            if "stem" not in out or out.get("stem") in (None, ""):
                alt = out.get("question") or out.get("title") or out.get("content") or ""
                if isinstance(alt, str) and alt:
                    out["stem"] = alt
            return out

        def _strip_and_normalize(obj):
            if isinstance(obj, dict):
                # quiz 顶层对象：补 title / quiz_id 兜底（QuizGenerateResult 强制要求）
                if isinstance(obj.get("questions"), list):
                    cleaned_obj: dict = {
                        k: _strip_and_normalize(v)
                        for k, v in obj.items()
                        if not (isinstance(k, str) and len(k) > 0 and k[0] == "_")
                    }
                    if not cleaned_obj.get("quiz_id") or not str(cleaned_obj.get("quiz_id", "")).strip():
                        cleaned_obj["quiz_id"] = "quiz-fallback-" + str(id(cleaned_obj))
                    if not cleaned_obj.get("title") or not isinstance(cleaned_obj.get("title"), str) or not cleaned_obj.get("title").strip():
                        alt = (
                            cleaned_obj.get("topic")
                            or cleaned_obj.get("knowledge_name")
                            or cleaned_obj.get("knowledge_point")
                            or cleaned_obj.get("quiz_id")
                            or ""
                        )
                        cleaned_obj["title"] = (alt + " · 闯关报告") if alt else "闯关报告"
                    return cleaned_obj
                if "question_id" in obj or "options" in obj:
                    # 疑似 Question，做字段兼容
                    return _normalize_question_dict({
                        k: _strip_and_normalize(v)
                        for k, v in obj.items()
                        if not (isinstance(k, str) and len(k) > 0 and k[0] == "_")
                    })
                return {
                    k: _strip_and_normalize(v)
                    for k, v in obj.items()
                    if not (isinstance(k, str) and len(k) > 0 and k[0] == "_")
                }
            if isinstance(obj, list):
                return [_strip_and_normalize(v) for v in obj]
            return obj

        try:
            if isinstance(quiz_data, dict) and "questions" in quiz_data:
                cleaned_quiz = _strip_and_normalize(quiz_data)
                questions = [Question.model_validate(q) for q in cleaned_quiz["questions"]]
            elif isinstance(quiz_data, list):
                cleaned_list = _strip_and_normalize(quiz_data)
                questions = [Question.model_validate(q) for q in cleaned_list]
                fallback_title = f"{request.quiz_id or 'quiz'} · 闯关报告"
                cleaned_quiz = {"questions": cleaned_list, "quiz_id": request.quiz_id or "quiz-fallback", "title": fallback_title}
            else:
                raise ReportGenerateError(message="quiz 数据无法解析出 questions 列表")
        except ReportGenerateError:
            logger.exception("generate_report quiz 解析失败，quiz_data.keys=%s", list(quiz_data.keys()) if isinstance(quiz_data, dict) else type(quiz_data).__name__)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("generate_report quiz 解析异常：%s | quiz_data.keys=%s", type(exc).__name__, list(quiz_data.keys()) if isinstance(quiz_data, dict) else type(quiz_data).__name__)
            raise ReportGenerateError(message=f"quiz questions 解析失败：{type(exc).__name__}") from exc

        # 在进入 ScoringService 前，用 QuizGenerateResult 校验一下最终题目集结构（含 title / questions 分布），
        # 不通过的话也用 fallback：把 questions 直接塞进去 + 补 title。这样即使 QuizGenerateResult.title/min_length 强约束也不会挂。
        try:
            from app.models.quiz import QuizGenerateResult
            QuizGenerateResult.model_validate({
                "quiz_id": cleaned_quiz.get("quiz_id") or request.quiz_id or "quiz-fallback",
                "title": cleaned_quiz.get("title") or (request.quiz_id + " · 闯关报告"),
                "questions": questions,
            })
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("QuizGenerateResult final re-validate failed (题目分布可能不满足3种题型齐全要求): %s -> fallback直接用questions继续算分", exc)
            # 不再强制抛错：QuizGenerateResult 目前仅在 _build_hardcoded_fallback / LLM 输出解析用，不影响 Score/Accuracy 计算。

        records = list(request.answer_records)

        try:
            score_summary = ScoringService.calc_score_summary(questions, records)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ScoringService.calc_score_summary failed: %s | questions_count=%d | records_count=%d", type(exc).__name__, len(questions), len(records))
            raise ReportGenerateError(message=f"算分失败：{type(exc).__name__}") from exc
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
                fixed = cls._normalize_report(result, payload)
                cls._scan_report_output_violation(fixed)
                return fixed
            if isinstance(result, dict):
                try:
                    parsed = ReportGenerateResult.model_validate(result)
                    fixed = cls._normalize_report(parsed, payload)
                    cls._scan_report_output_violation(fixed)
                    return fixed
                except (OutputContentViolationError, InputContentViolationError, InputTooShortError, InputTooLongError):
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Report L1 dict re-validate failed: %s", exc)
        except (OutputContentViolationError, InputContentViolationError, InputTooShortError, InputTooLongError):
            raise
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
    def _scan_report_output_violation(result: ReportGenerateResult) -> None:
        """Report 输出扫描：掌握点 / 薄弱点 / 三句总结 / 建议 / 金句。"""
        pieces: list[str] = []
        for x in result.mastered_points or []:
            if isinstance(x, str):
                pieces.append(x)
        for x in result.weak_points or []:
            if isinstance(x, str):
                pieces.append(x)
        for x in result.three_line_summary or []:
            if isinstance(x, str):
                pieces.append(x)
        if result.advice:
            pieces.append(result.advice)
        if result.share_quote:
            pieces.append(result.share_quote)
        hits = _OUTPUT_FILTER.find_all("\n".join(pieces))
        if hits:
            logger.warning("Report generate output hit sensitive words: %s", hits)
            raise OutputContentViolationError()

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
