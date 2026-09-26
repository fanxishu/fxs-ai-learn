from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.auth import create_access_token
from app.core.exceptions import InputContentViolationError, QuizNotFoundError
from app.models.user import (
    MAX_AVATAR_URL_LEN,
    MAX_NICKNAME_LEN,
    UserInfoSchema,
    UserLoginResponse,
    UserProfileResponse,
    QuizDetailResponse,
    QuizHistoryItem,
    QuizHistoryListResponse,
)
from app.repositories import (
    UserRepository,
    QuizSessionRepository,
    AnswerRecordRepository,
    ReportRepository,
)
from app.utils.content_filter import DFASensitiveWordFilter

logger = logging.getLogger(__name__)

_sensitive_filter: Optional[DFASensitiveWordFilter] = None


def _get_filter() -> DFASensitiveWordFilter:
    global _sensitive_filter
    if _sensitive_filter is None:
        _sensitive_filter = DFASensitiveWordFilter(file_path=settings.SENSITIVE_WORDS_FILE)
    return _sensitive_filter


async def _wx_jscode2session_openid(code: str) -> str:
    """返回 openid。
    策略：USE_MOCK_WX_LOGIN=true → mock_{code}；否则真实调用 jscode2session；失败/errcode≠0 → fallback_{code[:16]}。
    永不抛异常。"""
    if settings.USE_MOCK_WX_LOGIN:
        return f"mock_{code or 'empty'}"
    if not settings.WECHAT_APPID or not settings.WECHAT_APPSECRET:
        logger.warning("Wechat AppID/Secret missing, falling back")
        return f"fallback_cfg_{(code or 'empty')[:16]}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": settings.WECHAT_APPID,
                    "secret": settings.WECHAT_APPSECRET,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            body = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Wechat jscode2session network failed: %s", exc)
        return f"fallback_net_{(code or 'empty')[:16]}"
    if not isinstance(body, dict):
        return f"fallback_resp_{(code or 'empty')[:16]}"
    errcode = body.get("errcode")
    openid = body.get("openid")
    if (errcode is None or errcode == 0) and isinstance(openid, str) and openid:
        return openid
    logger.warning("Wechat jscode2session bad: errcode=%s errmsg=%s", errcode, body.get("errmsg"))
    return f"fallback_err_{(code or 'empty')[:16]}"


async def login_or_register_by_code(code: str) -> UserLoginResponse:
    openid = await _wx_jscode2session_openid(code or "")
    existing = await UserRepository.get_by_openid(openid)
    if existing:
        user_id = int(existing["id"])
        nickname = existing["nickname"]
        avatar_url = existing["avatar_url"] or ""
        total_xp = int(existing["total_xp"])
    else:
        user_id = await UserRepository.create(openid=openid, nickname="学习者", avatar_url="")
        nickname = "学习者"
        avatar_url = ""
        total_xp = 0
    token = create_access_token(user_id=user_id, openid=openid)
    return UserLoginResponse(
        token=token,
        user=UserInfoSchema(
            id=user_id,
            nickname=nickname,
            avatar_url=avatar_url,
            total_xp=total_xp,
        ),
    )


async def get_full_profile(user_id: int) -> UserProfileResponse:
    user = await UserRepository.get_by_id(int(user_id))
    stats = await UserRepository.get_profile_stats(int(user_id))
    if not user:
        return UserProfileResponse(
            id=int(user_id),
            nickname="学习者",
            avatar_url="",
            total_xp=0,
            quiz_count=0,
            correct_count=0,
            average_accuracy=0,
        )
    return UserProfileResponse(
        id=int(user["id"]),
        nickname=user["nickname"],
        avatar_url=user["avatar_url"] or "",
        total_xp=int(user["total_xp"]),
        quiz_count=int(stats["quiz_count"]),
        correct_count=int(stats["correct_count"]),
        average_accuracy=int(stats["average_accuracy"]),
    )


async def update_profile(
    user_id: int,
    nickname: Optional[str],
    avatar_url: Optional[str],
) -> UserProfileResponse:
    if nickname is not None:
        if len(nickname) == 0 or len(nickname) > MAX_NICKNAME_LEN:
            raise InputContentViolationError(message=f"昵称长度必须 1~{MAX_NICKNAME_LEN} 字")
        hits = _get_filter().find_all(nickname)
        if hits:
            raise InputContentViolationError(message=f"昵称包含敏感词：{'、'.join(hits)}")
    if avatar_url is not None:
        if len(avatar_url) > MAX_AVATAR_URL_LEN:
            raise InputContentViolationError(message=f"头像地址过长，必须 <= {MAX_AVATAR_URL_LEN}")
    await UserRepository.update_profile(
        user_id=int(user_id),
        nickname=nickname,
        avatar_url=avatar_url,
    )
    return await get_full_profile(int(user_id))


async def list_user_quizzes(
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> QuizHistoryListResponse:
    items, total = await QuizSessionRepository.list_by_user(
        user_id=int(user_id),
        page=page,
        page_size=page_size,
    )
    return QuizHistoryListResponse(
        items=[QuizHistoryItem(**x) for x in items],
        total=int(total),
        page=max(1, int(page)),
        page_size=max(1, min(100, int(page_size))),
    )


async def get_user_quiz_detail(user_id: int, quiz_id: str) -> QuizDetailResponse:
    q = await QuizSessionRepository.get_by_quiz_id_for_user(quiz_id=quiz_id, user_id=int(user_id))
    if not q:
        raise QuizNotFoundError()
    r = await AnswerRecordRepository.get_by_quiz_id_for_user(quiz_id=quiz_id, user_id=int(user_id))
    rp = await ReportRepository.get_by_quiz_id_for_user(quiz_id=quiz_id, user_id=int(user_id))
    answer_summary: Optional[dict] = None
    records: Optional[list] = None
    if r:
        records = r.get("records")
        answer_summary = {
            "total_questions": r["total_questions"],
            "correct_count": r["correct_count"],
            "accuracy": r["accuracy"],
            "created_at": r.get("created_at"),
        }
    return QuizDetailResponse(
        quiz_id=q["quiz_id"],
        title=q.get("title") or "",
        summary=q.get("summary"),
        user_input=q.get("user_input"),
        created_at=q.get("created_at"),
        questions=q.get("questions"),
        answer_records=records,
        answer_summary=answer_summary,
        report=rp.get("report") if rp else None,
    )
