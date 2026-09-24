from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.common import BaseSchema

QuestionType = Literal["single", "multiple", "judge"]


class QuizOption(BaseSchema):
    key: str = Field(..., min_length=1, max_length=4, description="选项键，如 A/B/C/D 或 对/错")
    text: str = Field(..., min_length=1, max_length=500, description="选项文本")


class Question(BaseSchema):
    model_config = ConfigDict(extra="allow")

    question_id: str = Field(..., min_length=1, max_length=64)
    question_type: QuestionType
    stem: str = Field(..., min_length=1, max_length=1000, description="题干")
    options: list[QuizOption] = Field(..., min_length=2, max_length=10)
    answer: str | list[str] = Field(..., description="正确答案；单选/判断为字符串，多选为字符串数组")
    knowledge_point: Optional[str] = Field(default=None, max_length=100)
    explanation: Optional[str] = Field(default=None, max_length=2000)
    difficulty: Optional[Annotated[int, Field(ge=1, le=5)]] = Field(default=None)

    @field_validator("options")
    @classmethod
    def _unique_option_keys(cls, v: list[QuizOption]) -> list[QuizOption]:
        keys = [o.key for o in v]
        if len(keys) != len(set(keys)):
            raise ValueError("options.key 必须唯一")
        return v

    @model_validator(mode="after")
    def _validate_shape(self) -> "Question":
        qtype = self.question_type
        n = len(self.options)
        if qtype == "judge":
            if n != 2:
                raise ValueError("判断题必须恰好有 2 个选项（对/错）")
            normalized = {o.key.strip().lower() for o in self.options}
            allowed_pairs = [
                {"对", "错"},
                {"是", "否"},
                {"t", "f"},
                {"true", "false"},
                {"y", "n"},
                {"yes", "no"},
                {"正确", "错误"},
            ]
            if not any(normalized == pair for pair in allowed_pairs):
                raise ValueError("判断题选项键必须是 对/错 或语义等价对")
            if isinstance(self.answer, list):
                raise ValueError("判断题答案必须是字符串")
            ans_keys = {o.key for o in self.options}
            if self.answer not in ans_keys:
                raise ValueError("判断题答案必须是 options 中的 key")
        elif qtype == "single":
            if n < 2:
                raise ValueError("单选题至少需要 2 个选项")
            if isinstance(self.answer, list):
                raise ValueError("单选题答案必须是字符串")
            ans_keys = {o.key for o in self.options}
            if self.answer not in ans_keys:
                raise ValueError("单选题答案必须是 options 中的 key")
        elif qtype == "multiple":
            if n < 2:
                raise ValueError("多选题至少需要 2 个选项")
            if not isinstance(self.answer, list) or len(self.answer) < 2:
                raise ValueError("多选题答案必须是长度 >=2 的字符串数组")
            ans_keys = {o.key for o in self.options}
            if not set(self.answer).issubset(ans_keys):
                raise ValueError("多选题答案必须全部是 options 中的 key")
            if len(self.answer) != len(set(self.answer)):
                raise ValueError("多选题答案存在重复")
        return self


class QuizGenerateRequest(BaseSchema):
    user_input: str = Field(..., min_length=5, max_length=500)
    question_count: Optional[Annotated[int, Field(ge=3, le=5)]] = Field(default=5)


class QuizGenerateResult(BaseSchema):
    quiz_id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=120)
    questions: list[Question] = Field(..., min_length=3, max_length=5)

    @field_validator("questions")
    @classmethod
    def _distribution(cls, v: list[Question]) -> list[Question]:
        counts = {"single": 0, "multiple": 0, "judge": 0}
        for q in v:
            counts[q.question_type] += 1
        if counts["single"] < 1:
            raise ValueError("题型分布需包含至少 1 道单选题")
        if counts["multiple"] < 1:
            raise ValueError("题型分布需包含至少 1 道多选题")
        if counts["judge"] < 1:
            raise ValueError("题型分布需包含至少 1 道判断题")
        return v
