from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user_id_required
from app.models.common import ok_response
from app.models.user import (
    QuizHistoryListResponse,
    QuizDetailResponse,
    UpdateProfileRequest,
    UserLoginResponse,
    UserProfileResponse,
    WxLoginRequest,
)
from app.services import user_service as svc

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/login", response_model_exclude_none=True)
async def wx_login(payload: WxLoginRequest):
    result: UserLoginResponse = await svc.login_or_register_by_code(payload.code)
    return ok_response(data=result.model_dump())


@router.get("/profile", response_model_exclude_none=True)
async def get_profile(user_id: int = Depends(get_current_user_id_required)):
    data: UserProfileResponse = await svc.get_full_profile(user_id)
    return ok_response(data=data.model_dump())


@router.put("/profile", response_model_exclude_none=True)
async def update_profile(
    payload: UpdateProfileRequest,
    user_id: int = Depends(get_current_user_id_required),
):
    data: UserProfileResponse = await svc.update_profile(
        user_id=user_id,
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
    )
    return ok_response(data=data.model_dump())


@router.get("/quizzes", response_model_exclude_none=True)
async def list_quizzes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: int = Depends(get_current_user_id_required),
):
    data: QuizHistoryListResponse = await svc.list_user_quizzes(
        user_id=user_id, page=page, page_size=page_size,
    )
    return ok_response(data=data.model_dump())


@router.get("/quizzes/{quiz_id}", response_model_exclude_none=True)
async def get_quiz_detail(
    quiz_id: str,
    user_id: int = Depends(get_current_user_id_required),
):
    data: QuizDetailResponse = await svc.get_user_quiz_detail(user_id=user_id, quiz_id=quiz_id)
    return ok_response(data=data.model_dump())
