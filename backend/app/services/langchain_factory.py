from __future__ import annotations

import uuid
import json
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.models.quiz import QuizGenerateResult

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "quiz_fixture_5q.json"


def _generate_quiz_id() -> str:
    return f"quiz-{uuid.uuid4().hex[:16]}"


def load_fallback_fixture() -> QuizGenerateResult:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw["quiz_id"] = _generate_quiz_id()
    return QuizGenerateResult.model_validate(raw)


class LLMFactory:
    @staticmethod
    def build_quiz_llm():
        if settings.USE_MOCK_LLM:
            return MockQuizLLM()
        return DeepSeekQuizLLM()

    @staticmethod
    def build_report_llm():
        if settings.USE_MOCK_LLM:
            return MockReportLLM()
        return DeepSeekReportLLM()


class MockQuizLLM:
    async def ainvoke_structured(self, request) -> Optional[QuizGenerateResult]:
        try:
            fx = load_fallback_fixture()
            return fx
        except Exception as exc:  # noqa: BLE001
            logger.warning("MockQuizLLM fixture parse failed: %s", exc)
            return None


class DeepSeekQuizLLM:
    def __init__(self):
        self._base_url = settings.DEEPSEEK_BASE_URL
        self._model = settings.DEEPSEEK_MODEL
        self._temperature = settings.DEEPSEEK_TEMPERATURE_QUIZ
        self._timeout = settings.DEEPSEEK_TIMEOUT
        self._retries = settings.DEEPSEEK_MAX_RETRIES

    async def ainvoke_structured(self, request) -> Optional[QuizGenerateResult]:
        if not settings.DEEPSEEK_API_KEY:
            logger.warning("DeepSeek API Key not configured, use fallback fixture")
            return None
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI

            schema_desc = QuizGenerateResult.model_json_schema()
            schema_json = json.dumps(schema_desc, ensure_ascii=False)
            escaped_schema = schema_json.replace("{", "{{").replace("}", "}}")

            system = (
                "你是一名优秀的出题专家。请根据用户输入的学习主题，生成 {question_count} 道自测题。"
                "题型必须同时包含单选题（question_type=single）、多选题（question_type=multiple）"
                "和判断题（question_type=judge），且三种题型缺一不可。"
                "你必须严格输出符合下方 JSON Schema 的 JSON 对象，"
                "禁止包含任何 Markdown 代码块、多余说明文字或前缀后缀。\n\n"
                "## JSON Schema\n```json\n"
                + escaped_schema
                + "\n```\n"
            )
            human = "学习主题：\n{user_input}\n\n请直接输出符合 Schema 的 JSON 对象。"

            prompt = ChatPromptTemplate.from_messages(
                [("system", system), ("human", human)]
            ).partial(question_count=str(request.question_count))

            llm = ChatOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=self._base_url,
                model=self._model,
                temperature=self._temperature,
                timeout=self._timeout,
                max_retries=self._retries,
            ).bind(response_format={"type": "json_object"})

            chain = prompt | llm
            raw_msg = await chain.ainvoke({"user_input": request.user_input})
            content = getattr(raw_msg, "content", None) or ""
            if not isinstance(content, str) or not content.strip():
                logger.warning("DeepSeekQuizLLM empty content returned")
                return None
            try:
                parsed = QuizGenerateResult.model_validate_json(content)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DeepSeekQuizLLM JSON->Pydantic parse failed: %s", exc)
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines and lines[0].strip().startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()
                parsed = QuizGenerateResult.model_validate_json(cleaned)
            if not parsed.quiz_id:
                parsed.quiz_id = _generate_quiz_id()
            return parsed
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepSeekQuizLLM invoke failed: %s", exc)
            return None


class MockReportLLM:
    async def ainvoke_structured(self, payload):
        from app.models.report import ReportGenerateResult

        per_knowledge = payload.get("per_knowledge") or []
        ok = []
        weak = []
        for m in per_knowledge:
            kp = getattr(m, "knowledge_point", None) or m.get("knowledge_point") if isinstance(m, dict) else None
            mastery_val = getattr(m, "mastery", None)
            if mastery_val is None and isinstance(m, dict):
                mastery_val = m.get("mastery")
            if kp is None or mastery_val is None:
                continue
            if mastery_val >= 0.8:
                ok.append(kp)
            elif mastery_val <= 0.6:
                weak.append(kp)
        ok = (ok or payload.get("mastered_points") or ["暂无"])[:5]
        weak = (weak or payload.get("weak_points") or ["暂无"])[:5]

        acc = int(payload.get("accuracy", 0))
        acc = max(0, min(100, acc))
        level = "优秀" if acc >= 80 else ("良好" if acc >= 60 else "有待提升")

        data = {
            "accuracy": acc,
            "mastered_points": ok,
            "weak_points": weak,
            "three_line_summary": [
                f"本次答题正确率约为 {acc} 分，整体表现{level}。",
                f"已掌握知识点 {len(ok)} 个，薄弱知识点 {len(weak)} 个。",
                "建议针对薄弱点重点复习，并多做同类练习巩固掌握。",
            ],
            "advice": "建议按照掌握度从低到高依次复习薄弱知识点，每个知识点配合 2~3 道题目进行巩固。",
            "share_quote": "每天进步一点点，终将成就大大的自己！",
        }
        return ReportGenerateResult.model_validate(data)


class DeepSeekReportLLM:
    def __init__(self):
        self._base_url = settings.DEEPSEEK_BASE_URL
        self._model = settings.DEEPSEEK_MODEL
        self._temperature = settings.DEEPSEEK_TEMPERATURE_REPORT
        self._timeout = settings.DEEPSEEK_TIMEOUT
        self._retries = settings.DEEPSEEK_MAX_RETRIES

    async def ainvoke_structured(self, payload) -> Optional[object]:
        if not settings.DEEPSEEK_API_KEY:
            logger.warning("DeepSeek API Key not configured for report, use mock fallback")
            return None
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI
            from app.models.report import ReportGenerateResult

            schema_desc = ReportGenerateResult.model_json_schema()
            schema_json = json.dumps(schema_desc, ensure_ascii=False)
            escaped_schema = schema_json.replace("{", "{{").replace("}", "}}")

            system = (
                "你是一名耐心的学习教练。根据用户的答题记录和得分情况，生成一份温暖且实用的分析报告。"
                "你必须严格输出符合下方 JSON Schema 的 JSON 对象："
                "- accuracy 是 0-100 的整数；"
                "- three_line_summary 必须是长度恰好为 3 的非空字符串数组；"
                "- mastered_points 和 weak_points 必须是非空字符串数组；"
                "- advice 和 share_quote 必须是非空字符串。"
                "禁止包含任何 Markdown 代码块或多余说明文字。\n\n"
                "## JSON Schema\n```json\n"
                + escaped_schema
                + "\n```\n"
            )
            human = (
                "以下是答题情况：\n"
                "- 总体得分：{score_summary}\n"
                "- 知识点掌握详情：{per_knowledge_mastery}\n"
                "- 答题记录摘要：{answer_records_brief}\n"
                "\n请直接输出符合 Schema 的 JSON 对象。"
            )
            prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
            llm = ChatOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=self._base_url,
                model=self._model,
                temperature=self._temperature,
                timeout=self._timeout,
                max_retries=self._retries,
            ).bind(response_format={"type": "json_object"})

            chain = prompt | llm
            raw_msg = await chain.ainvoke({
                "score_summary": json.dumps(payload.get("score_summary"), ensure_ascii=False),
                "per_knowledge_mastery": json.dumps(
                    [
                        m.model_dump() if hasattr(m, "model_dump") else (dict(m) if isinstance(m, dict) else {})
                        for m in payload.get("per_knowledge_mastery", [])
                    ],
                    ensure_ascii=False,
                ),
                "answer_records_brief": json.dumps(
                    payload.get("answer_records_brief", []),
                    ensure_ascii=False,
                ),
            })
            content = getattr(raw_msg, "content", None) or ""
            if not isinstance(content, str) or not content.strip():
                logger.warning("DeepSeekReportLLM empty content returned")
                return None
            try:
                parsed = ReportGenerateResult.model_validate_json(content)
            except Exception as exc:  # noqa: BLE001
                logger.warning("DeepSeekReportLLM JSON->Pydantic parse failed: %s", exc)
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines and lines[0].strip().startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    cleaned = "\n".join(lines).strip()
                parsed = ReportGenerateResult.model_validate_json(cleaned)
            return parsed
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepSeekReportLLM invoke failed: %s", exc)
            return None
