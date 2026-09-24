from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import BaseSchema
from app.models.quiz import Question


class AnswerRecord(BaseSchema):
    question_id: str = Field(..., min_length=1, max_length=64)
    user_answer: str | list[str] = Field(..., description="用户答案")
    is_correct: bool
    time_spent_ms: Optional[Annotated[int, Field(ge=0)]] = Field(default=None)


class KnowledgePointMastery(BaseSchema):
    knowledge_point: str = Field(..., min_length=1, max_length=100)
    correct_count: Annotated[int, Field(ge=0)] = 0
    total_count: Annotated[int, Field(ge=1)] = 1
    mastery: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="掌握度 0-1"
    )


class ScoreSummary(BaseSchema):
    total_count: Annotated[int, Field(ge=1)]
    correct_count: Annotated[int, Field(ge=0)]
    accuracy: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="正确率 0-1"
    )
    score: Annotated[int, Field(ge=0, le=100)] = Field(
        ..., description="百分制分数"
    )
    per_knowledge: list[KnowledgePointMastery] = Field(default_factory=list)


class ReportGenerateRequest(BaseSchema):
    model_config = ConfigDict(extra="allow")

    quiz_id: str = Field(..., min_length=1, max_length=64)
    quiz: Any = Field(..., description="题目数据，支持 {questions:[...]} 或 Question 列表或 QuizGenerateResult")
    answer_records: list[AnswerRecord] = Field(..., min_length=1)

    @field_validator("quiz")
    @classmethod
    def _coerce_quiz(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, QuizGenerateResult):
            return v.model_dump()
        if isinstance(v, BaseModel):
            return v.model_dump()
        if isinstance(v, dict):
            return v
        if isinstance(v, list):
            return {"questions": v}
        raise ValueError("quiz 必须是 dict/list/QuizGenerateResult")


class ReportGenerateResult(BaseSchema):
    accuracy: Annotated[int, Field(ge=0, le=100)] = Field(
        ..., description="百分制正确率 0-100"
    )
    mastered_points: list[str] = Field(
        default_factory=list, description="已掌握知识点，空数组将自动填充占位"
    )
    weak_points: list[str] = Field(
        default_factory=list, description="薄弱知识点，空数组将自动填充占位"
    )
    three_line_summary: list[str] = Field(
        ..., min_length=3, max_length=3, description="三句总结，长度必须为 3"
    )
    advice: str = Field(..., min_length=1, max_length=2000, description="AI 建议")
    share_quote: str = Field(
        ..., min_length=1, max_length=500, description="分享海报金句"
    )

    @field_validator("three_line_summary")
    @classmethod
    def _three_non_empty(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError("three_line_summary 长度必须为 3")
        for i, line in enumerate(v):
            if not line or not line.strip():
                raise ValueError(f"three_line_summary[{i}] 不能为空")
        return v

    @field_validator("mastered_points", "weak_points")
    @classmethod
    def _non_empty_items(cls, v: list[str]) -> list[str]:
        if not v:
            return ["暂无"]
        cleaned = [x.strip() for x in v if x and x.strip()]
        return cleaned or ["暂无"]


# re-export for convenience
from app.models.quiz import QuizGenerateResult  # noqa: E402,F401
