import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import create_access_token  # noqa: E402


def _bearer(user_id: int = 1, openid: str = "oid_test") -> dict[str, str]:
    tok = create_access_token(user_id, openid)
    return {"Authorization": f"Bearer {tok}"}


class TestQuizGenerateHappyPath:
    @pytest.mark.asyncio
    async def test_quiz_generate_200_ok_code_0(self, client):
        payload = {"user_input": "Python 基础入门语法与数据类型", "question_count": 5}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "ok" or body["message"]
        assert "data" in body and body["data"] is not None
        assert body["data"]["quiz_id"]
        assert body["data"]["title"]
        qs = body["data"]["questions"]
        assert isinstance(qs, list) and 3 <= len(qs) <= 5

    @pytest.mark.asyncio
    async def test_quiz_generate_distribution_has_all_three_types(self, client):
        payload = {"user_input": "Python 基础入门语法与数据类型"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        body = resp.json()
        qs = body["data"]["questions"]
        counts = {"single": 0, "multiple": 0, "judge": 0}
        for q in qs:
            counts[q["question_type"]] += 1
        assert counts["single"] >= 1
        assert counts["multiple"] >= 1
        assert counts["judge"] >= 1

    @pytest.mark.asyncio
    async def test_quiz_generate_question_count_3_matches(self, client):
        payload = {"user_input": "Python 函数定义与调用示例", "question_count": 3}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        body = resp.json()
        assert body["code"] == 0
        assert len(body["data"]["questions"]) == 3

    @pytest.mark.asyncio
    async def test_quiz_generate_every_question_required_fields(self, client):
        payload = {"user_input": "Python 列表 list 常用操作方法"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        body = resp.json()
        qs = body["data"]["questions"]
        for q in qs:
            assert q["question_id"].strip() != ""
            assert q["stem"].strip() != ""
            assert "question_type" in q
            assert isinstance(q["options"], list) and len(q["options"]) >= 2
            assert q["knowledge_point"].strip() != ""
            assert q["explanation"].strip() != ""


class TestQuizGenerateInputValidation:
    @pytest.mark.asyncio
    async def test_quiz_generate_empty_user_input_code_4000(self, client):
        payload = {"user_input": ""}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000
        assert body["data"] is None

    @pytest.mark.asyncio
    async def test_quiz_generate_short_input_abc_code_4000(self, client):
        payload = {"user_input": "abc"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000

    @pytest.mark.asyncio
    async def test_quiz_generate_count_6_over_max_code_4000(self, client):
        payload = {"user_input": "Python 基础入门足够长度的输入文本", "question_count": 6}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000

    @pytest.mark.asyncio
    async def test_quiz_generate_missing_user_input_code_4000(self, client):
        payload = {"question_count": 5}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000


class TestQuizGenerateCleanerAndFilter:
    @pytest.mark.asyncio
    async def test_quiz_generate_strips_html_and_still_succeeds_code_0(self, client):
        payload = {"user_input": "<p>Python <b>列表</b> 推导式<br/>用法示例</p>", "question_count": 5}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

    @pytest.mark.asyncio
    async def test_quiz_generate_sensitive_赌博_code_4001(self, client):
        payload = {"user_input": "赌博秘籍分享 博彩网站推荐 必中秘诀"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4001
        assert "违规内容" in body["message"] or "敏感" in body["message"]

    @pytest.mark.asyncio
    async def test_quiz_generate_sensitive_hits_in_data(self, client):
        payload = {"user_input": "六合彩 时时彩 赌球技巧大公开"}
        resp = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(1))
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4001
        assert isinstance(body["data"], dict)
        assert isinstance(body["data"].get("hits"), list)
        assert len(body["data"]["hits"]) >= 2
