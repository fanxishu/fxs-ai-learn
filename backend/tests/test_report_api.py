import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

FIXTURE_PATH = BACKEND_ROOT / "tests" / "fixtures" / "quiz_fixture_5q.json"


def _load_quiz_dict():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def quiz_dict():
    return _load_quiz_dict()


@pytest.fixture
def records_3of5(quiz_dict):
    qs = quiz_dict["questions"]
    wrong_map = {"A": "B", "B": "A", "对": "错", "错": "对"}
    return [
        {"question_id": qs[0]["question_id"], "user_answer": qs[0]["answer"], "is_correct": True, "time_spent_ms": 1000},
        {"question_id": qs[1]["question_id"], "user_answer": wrong_map.get(qs[1]["answer"], "A"), "is_correct": False, "time_spent_ms": 500},
        {"question_id": qs[2]["question_id"], "user_answer": qs[2]["answer"], "is_correct": True, "time_spent_ms": 600},
        {"question_id": qs[3]["question_id"], "user_answer": ["A", "B"], "is_correct": False, "time_spent_ms": 2000},
        {"question_id": qs[4]["question_id"], "user_answer": qs[4]["answer"], "is_correct": True, "time_spent_ms": 300},
    ]


@pytest.fixture
def records_5of5(quiz_dict):
    return [
        {"question_id": q["question_id"], "user_answer": q["answer"], "is_correct": True, "time_spent_ms": 800}
        for q in quiz_dict["questions"]
    ]


class TestReportGenerateHappyPath:
    @pytest.mark.asyncio
    async def test_report_generate_code_0_and_accuracy_60(self, client, quiz_dict, records_3of5):
        payload = {
            "quiz_id": quiz_dict["quiz_id"],
            "quiz": quiz_dict,
            "answer_records": records_3of5,
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["message"] == "ok" or body["message"]
        assert body["data"] is not None
        assert body["data"]["accuracy"] == 60

    @pytest.mark.asyncio
    async def test_report_generate_accuracy_100_mastered_not_sentinel(self, client, quiz_dict, records_5of5):
        payload = {
            "quiz_id": quiz_dict["quiz_id"],
            "quiz": quiz_dict,
            "answer_records": records_5of5,
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["accuracy"] == 100
        assert "暂无" not in body["data"]["mastered_points"]

    @pytest.mark.asyncio
    async def test_report_generate_three_line_summary_len_3_non_empty(self, client, quiz_dict, records_3of5):
        payload = {
            "quiz_id": quiz_dict["quiz_id"],
            "quiz": quiz_dict,
            "answer_records": records_3of5,
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        body = resp.json()
        summary = body["data"]["three_line_summary"]
        assert len(summary) == 3
        for line in summary:
            assert isinstance(line, str) and line.strip() != ""

    @pytest.mark.asyncio
    async def test_report_generate_advice_and_share_quote_non_empty(self, client, quiz_dict, records_3of5):
        payload = {
            "quiz_id": quiz_dict["quiz_id"],
            "quiz": quiz_dict,
            "answer_records": records_3of5,
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        body = resp.json()
        d = body["data"]
        assert isinstance(d["advice"], str) and d["advice"].strip() != ""
        assert isinstance(d["share_quote"], str) and d["share_quote"].strip() != ""


class TestReportGenerateInputValidation:
    @pytest.mark.asyncio
    async def test_report_generate_empty_records_code_4000(self, client, quiz_dict):
        payload = {
            "quiz_id": quiz_dict["quiz_id"],
            "quiz": quiz_dict,
            "answer_records": [],
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000
        assert body["data"] is None

    @pytest.mark.asyncio
    async def test_report_generate_missing_quiz_id_code_4000(self, client, quiz_dict, records_3of5):
        payload = {
            "quiz": quiz_dict,
            "answer_records": records_3of5,
        }
        resp = await client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000

    @pytest.mark.asyncio
    async def test_report_generate_missing_records_field_code_4000(self, client, quiz_dict):
        payload = {"quiz_id": quiz_dict["quiz_id"], "quiz": quiz_dict}
        resp = await client.post("/api/v1/report/generate", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 4000
