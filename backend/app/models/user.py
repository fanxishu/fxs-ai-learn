from __future__ import annotations

from typing import Optional

from app.models.common import BaseSchema


MAX_NICKNAME_LEN = 20
MAX_AVATAR_URL_LEN = 500


class WxLoginRequest(BaseSchema):
    code: str


class UserInfoSchema(BaseSchema):
    id: int
    nickname: str = "学习者"
    avatar_url: str = ""
    total_xp: int = 0


class UserLoginResponse(BaseSchema):
    token: str
    user: UserInfoSchema


class UserProfileResponse(BaseSchema):
    id: int
    nickname: str = "学习者"
    avatar_url: str = ""
    total_xp: int = 0
    quiz_count: int = 0
    correct_count: int = 0
    average_accuracy: int = 0


class UpdateProfileRequest(BaseSchema):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class QuizHistoryItem(BaseSchema):
    quiz_id: str
    title: str = ""
    accuracy: int = 0
    question_count: int = 0
    created_at: Optional[str] = None


class QuizHistoryListResponse(BaseSchema):
    items: list[QuizHistoryItem]
    total: int = 0
    page: int = 1
    page_size: int = 10


class QuizDetailResponse(BaseSchema):
    quiz_id: str
    title: str = ""
    summary: Optional[str] = None
    user_input: Optional[str] = None
    created_at: Optional[str] = None
    questions: Optional[list] = None
    answer_records: Optional[list] = None
    answer_summary: Optional[dict] = None
    report: Optional[dict] = None
