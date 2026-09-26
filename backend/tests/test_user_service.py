from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.services import user_service as svc


@pytest.fixture
def _always_mock_mode():
    prev = settings.USE_MOCK_WX_LOGIN
    settings.USE_MOCK_WX_LOGIN = True
    yield
    settings.USE_MOCK_WX_LOGIN = prev


@pytest.mark.asyncio
async def test_mock_login_registers_new_user(_always_mock_mode, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    # First fetchone: SELECT by openid → None -> register, INSERT lastrowid=11, THEN SELECT again in get_by_openid -> returns user row
    async def _side_effect(*args, **kw):
        return None
    cur.fetchone.side_effect = _side_effect
    cur.lastrowid = 11
    result = await svc.login_or_register_by_code("wxabc")
    assert result.user.id == 11 and result.user.total_xp == 0
    # verify token is usable by parsing
    from app.core.auth import parse_token
    payload = parse_token(result.token)
    assert payload["user_id"] == 11 and payload["openid"] == "mock_wxabc"


@pytest.mark.asyncio
async def test_login_existing_user_returns_profile(_always_mock_mode, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    # SELECT by openid → row
    cur.fetchone.return_value = (
        7, "mock_old1", "鱼皮同学", "", 42,
        datetime(2026, 1, 1), datetime(2026, 2, 1),
    )
    result = await svc.login_or_register_by_code("old1")
    assert result.user.id == 7 and result.user.nickname == "鱼皮同学" and result.user.total_xp == 42
    # no INSERT expected (only get_by_openid SELECT once + close? at least not INSERT)
    insert_calls = [c for c in cur.execute.await_args_list if str(c.args[0]).upper().startswith("INSERT")]
    assert len(insert_calls) == 0, f"should not INSERT for existing user: {insert_calls}"


@pytest.mark.asyncio
async def test_update_profile_contains_sensitive_word_blocks_3001():
    """敏感昵称抛 3001 InputContentViolationError"""
    from app.core.exceptions import InputContentViolationError
    with patch.object(svc.UserRepository, "get_by_id", AsyncMock(return_value=None)):
        with patch.object(svc.UserRepository, "update_profile", AsyncMock()):
            with pytest.raises(InputContentViolationError) as ei:
                await svc.update_profile(1, "我是大傻逼呵呵", None)
            assert ei.value.code == 3001
            svc.UserRepository.update_profile.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_profile_too_long_blocks():
    from app.core.exceptions import InputContentViolationError
    with patch.object(svc.UserRepository, "update_profile", AsyncMock()):
        with pytest.raises(InputContentViolationError):
            await svc.update_profile(1, "a" * 30, None)


@pytest.mark.asyncio
async def test_update_profile_valid_calls_repo(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    # UPDATE profile → then get_full_profile: 1. SELECT user by id 2. SELECT stats aggregation
    user_row = (1, "oid", "新昵称", "", 10, datetime(2026, 1, 1), datetime(2026, 2, 1))
    stats_row = (2, 7, 10)  # 7/10 = 70%
    # Each fetchone call: UPDATE no fetch -> GET 1 -> GET 2
    cur.fetchone.side_effect = [user_row, stats_row]
    with patch("app.services.user_service._get_filter", return_value=MagicMock(find_all=lambda text: [])):
        prof = await svc.update_profile(1, "新昵称", None)
    assert prof.nickname == "新昵称"
    assert prof.quiz_count == 2 and prof.correct_count == 7 and prof.average_accuracy == 70


@pytest.mark.asyncio
async def test_get_full_profile_uses_stats_aggregation(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    # SELECT user → then SELECT stats (count/sum)
    call_index = {"n": 0}
    def _fetch():
        call_index["n"] += 1
        if call_index["n"] == 1:
            return (1, "oid1", "学习者", "", 100, datetime(2026,1,1), datetime(2026,2,1))
        return (5, 18, 24)  # quiz_count=5, correct=18, total_q=24 → 75%
    cur.fetchone.side_effect = lambda: _fetch()
    p = await svc.get_full_profile(1)
    assert p.id == 1 and p.total_xp == 100
    assert p.quiz_count == 5 and p.correct_count == 18
    assert p.average_accuracy == 75  # 18/24 = 0.75

@pytest.mark.asyncio
async def test_quiz_detail_越权_returns_4001_not_found(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = None  # quiz not found for user
    from app.core.exceptions import QuizNotFoundError
    with pytest.raises(QuizNotFoundError) as ei:
        await svc.get_user_quiz_detail(1, "q_not_mine")
    assert ei.value.code == 4001
