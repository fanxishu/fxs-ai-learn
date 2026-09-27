import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_health_check_ok(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["project_name"] == "智能 AI 闯关学习小程序"
    assert "use_mock_llm" in body
