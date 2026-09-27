from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.core.auth import get_current_user_id_required
from app.core.exceptions import FishAIException, ParamInvalidError
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
from app.services import avatar_service

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


@router.post("/avatar", response_model_exclude_none=True)
async def upload_avatar(
    user_id: int = Depends(get_current_user_id_required),
    file: UploadFile = File(...),
):
    try:
        if file.size is not None and file.size > avatar_service.MAX_AVATAR_BYTES:
            raise ParamInvalidError(message="头像不能超过 2MB")
        content = await file.read(avatar_service.MAX_AVATAR_BYTES + 1)
    finally:
        await file.close()
    avatar_url = await avatar_service.save_avatar(user_id, content)
    return ok_response(data={"avatar_url": avatar_url})


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    path = avatar_service.get_avatar_path(filename)
    if path is None or not path.is_file():
        raise FishAIException(code=4001, message="头像不存在")
    return FileResponse(
        path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
