from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.auth import create_access_token


def _bearer(user_id: int = 1, openid: str = "oid_test") -> dict[str, str]:
    tok = create_access_token(user_id, openid)
    return {"Authorization": f"Bearer {tok}"}


@pytest.mark.asyncio
async def test_login_public_returns_token_and_user(client, db_pool_cur):
    """POST /user/login 公开（无需 token），mock 模式返回 mock_ + code"""
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    from unittest.mock import MagicMock
    cur.fetchone.return_value = None
    cur.lastrowid = 9
    resp = await client.post("/api/v1/user/login", json={"code": "abc123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0 and body["message"] == "ok", body
    data = body["data"]
    assert data["user"]["id"] == 9
    assert data["user"]["nickname"] == "学习者"
    assert data["user"]["total_xp"] == 0
    assert isinstance(data["token"], str) and len(data["token"]) > 20


@pytest.mark.asyncio
async def test_profile_without_token_returns_2001(client):
    """GET /user/profile 匿名 = 2001 未登录"""
    resp = await client.get("/api/v1/user/profile")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 2001, body


@pytest.mark.asyncio
async def test_profile_with_token_ok(client, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    call_n = {"n": 0}
    def _fetch():
        call_n["n"] += 1
        if call_n["n"] == 1:
            return (1, "oid", "同学", "", 30, datetime(2026,1,1), datetime(2026,2,1))
        return (2, 7, 10)  # 7/10 = 70%
    cur.fetchone.side_effect = lambda: _fetch()
    resp = await client.get("/api/v1/user/profile", headers=_bearer(1))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0, body
    d = body["data"]
    assert d["nickname"] == "同学" and d["total_xp"] == 30
    assert d["quiz_count"] == 2 and d["correct_count"] == 7 and d["average_accuracy"] == 70


@pytest.mark.asyncio
async def test_update_profile_sensitive_blocked_3001(client):
    bad = {"nickname": "我是傻逼测试"}
    resp = await client.put("/api/v1/user/profile", json=bad, headers=_bearer(1))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 3001, body


@pytest.mark.asyncio
async def test_list_quizzes_pagination(client, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    def _sel():
        return []
    cur.fetchone.side_effect = lambda: (12,)
    cur.fetchall.return_value = []
    resp = await client.get("/api/v1/user/quizzes?page=1&page_size=20", headers=_bearer(1))
    body = resp.json()
    assert body["code"] == 0, body
    d = body["data"]
    assert d["page"] == 1 and d["page_size"] == 20 and d["total"] == 12


@pytest.mark.asyncio
async def test_quiz_detail_other_user_returns_4001(client, db_pool_cur):
    _, cur = db_pool_cur
    cur.fetchone.return_value = None
    resp = await client.get("/api/v1/user/quizzes/not-mine", headers=_bearer(1))
    body = resp.json()
    assert body["code"] == 4001, body


@pytest.mark.asyncio
async def test_put_profile_extra_field_4000(client):
    """Pydantic extra='forbid'：额外字段 → 4000"""
    resp = await client.put(
        "/api/v1/user/profile",
        json={"nickname": "ok", "bonus": 1},
        headers=_bearer(1),
    )
    body = resp.json()
    assert body["code"] in (4000, 2001), body
