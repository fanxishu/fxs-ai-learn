import time
from unittest.mock import MagicMock

import jwt as _jwt
import pytest

from app.core.auth import (
    create_access_token,
    parse_token,
    get_current_user_id_required,
    get_current_user_id_optional,
)
from app.core.exceptions import UnauthorizedError, TokenExpiredError
from app.core.config import settings


def test_tr31_token_payload_roundtrip():
    tok = create_access_token(123, "openid_abc")
    assert isinstance(tok, str) and len(tok) > 20
    payload = parse_token(tok)
    assert payload["user_id"] == 123
    assert payload["openid"] == "openid_abc"
    assert "exp" in payload and "iat" in payload


def test_tr32_tampered_token_raises_2001():
    tok = create_access_token(1, "x")
    bad = tok[:-4] + ("A" if tok[-4] != "A" else "B") + tok[-3:]
    with pytest.raises(UnauthorizedError) as ei:
        parse_token(bad)
    assert ei.value.code == 2001


def test_tr32_expired_raises_2002():
    old_days = settings.JWT_EXPIRE_DAYS
    try:
        settings.JWT_EXPIRE_DAYS = -1
        expired = create_access_token(1, "x")
    finally:
        settings.JWT_EXPIRE_DAYS = old_days
    with pytest.raises(TokenExpiredError) as ei:
        parse_token(expired)
    assert ei.value.code == 2002


def test_tr33_alg_none_blocked_by_whitelist():
    forged = _jwt.encode(
        {"user_id": 999, "openid": "x", "exp": int(time.time()) + 3600, "iat": int(time.time())},
        key="",
        algorithm="none",
    )
    with pytest.raises(UnauthorizedError):
        parse_token(forged)


@pytest.mark.asyncio
async def test_depends_optional_anonymous_returns_none():
    assert await get_current_user_id_optional(None) is None


@pytest.mark.asyncio
async def test_depends_required_anonymous_raises_2001():
    with pytest.raises(UnauthorizedError) as ei:
        await get_current_user_id_required(None)
    assert ei.value.code == 2001


@pytest.mark.asyncio
async def test_depends_valid_token_returns_user_id():
    tok = create_access_token(42, "oid1")
    cred = MagicMock(scheme="Bearer", credentials=tok)
    assert await get_current_user_id_optional(cred) == 42
    assert await get_current_user_id_required(cred) == 42


@pytest.mark.asyncio
async def test_depends_bad_scheme_treated_as_anonymous():
    cred = MagicMock(scheme="Basic", credentials="abc:123")
    assert await get_current_user_id_optional(cred) is None
    with pytest.raises(UnauthorizedError):
        await get_current_user_id_required(cred)
