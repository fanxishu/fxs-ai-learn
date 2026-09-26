import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest_asyncio.fixture(autouse=True)
def _mock_db_lifespan():
    """阻止 pytest 触发真实 MySQL 连接；所有 DB 相关测试单独 patch。"""
    fake_pool = MagicMock(name="FakePool")
    fake_conn = MagicMock(name="FakeConn")
    fake_cur = MagicMock(name="FakeCur")
    fake_cur.execute = AsyncMock(name="fake_cur.execute")
    fake_cur.fetchone = AsyncMock(name="fake_cur.fetchone", return_value=None)
    fake_cur.fetchall = AsyncMock(name="fake_cur.fetchall", return_value=[])
    fake_cur.lastrowid = 1
    # async with conn.cursor() as cur → cursor_ctx yields fake_cur
    cursor_ctx = MagicMock(name="cursor_ctx")
    cursor_ctx.__aenter__ = AsyncMock(name="cursor_ctx.__aenter__", return_value=fake_cur)
    cursor_ctx.__aexit__ = AsyncMock(name="cursor_ctx.__aexit__", return_value=False)
    fake_conn.cursor = MagicMock(name="fake_conn.cursor", return_value=cursor_ctx)
    fake_conn.commit = AsyncMock(name="fake_conn.commit")
    fake_conn.rollback = AsyncMock(name="fake_conn.rollback")
    # async with pool.acquire() as conn → acquire_ctx yields fake_conn
    acquire_ctx = MagicMock(name="acquire_ctx")
    acquire_ctx.__aenter__ = AsyncMock(name="acquire_ctx.__aenter__", return_value=fake_conn)
    acquire_ctx.__aexit__ = AsyncMock(name="acquire_ctx.__aexit__", return_value=False)
    fake_pool.acquire = MagicMock(name="fake_pool.acquire", return_value=acquire_ctx)
    fake_pool.close = MagicMock(name="fake_pool.close")
    fake_pool.wait_closed = AsyncMock(name="fake_pool.wait_closed")

    with (
        patch("app.core.db.create_db_pool", new_callable=AsyncMock, return_value=fake_pool),
        patch("app.core.db.close_db_pool", new_callable=AsyncMock),
        patch("app.core.db._pool", new=fake_pool),
    ):
        yield fake_pool, fake_cur


@pytest_asyncio.fixture
async def db_pool_cur(_mock_db_lifespan):
    """返回 (fake_pool, fake_cursor)，供 Repository 单测断言 SQL execute 参数。"""
    return _mock_db_lifespan


from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac
