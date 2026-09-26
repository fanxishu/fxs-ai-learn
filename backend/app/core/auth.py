from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import UnauthorizedError, TokenExpiredError

logger = logging.getLogger(__name__)

_security = HTTPBearer(auto_error=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, openid: str) -> str:
    expire = _utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "user_id": int(user_id),
        "openid": str(openid),
        "exp": expire,
        "iat": _utcnow(),
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def parse_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={
                "require": ["exp", "user_id", "openid"],
                "verify_signature": True,
                "verify_exp": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(message="登录凭证无效，请重新登录") from exc


def _extract_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials is None:
        return None
    scheme = credentials.scheme or ""
    if scheme.lower() != "bearer":
        return None
    token = credentials.credentials or ""
    return token.strip() or None


async def get_current_user_id_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> int:
    token = _extract_bearer_token(credentials)
    if not token:
        raise UnauthorizedError()
    payload = parse_token(token)
    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise UnauthorizedError(message="登录凭证无效，请重新登录")
    return user_id


async def get_current_user_id_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> Optional[int]:
    token = _extract_bearer_token(credentials)
    if not token:
        return None
    try:
        payload = parse_token(token)
    except Exception:  # noqa: BLE001
        logger.warning("Optional auth failed, treating as anonymous")
        return None
    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        return None
    return user_id
