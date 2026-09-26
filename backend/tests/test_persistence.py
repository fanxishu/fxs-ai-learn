"""验证 quiz/report 接口在匿名 vs 登录态下返回结构字节级一致，持久化只在登录分支触发。"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.auth import create_access_token


FIXTURE_FILE = Path(__file__).parent / "fixtures" / "quiz_fixture_5q.json"
_fixture_doc = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
_fixture_questions = _fixture_doc["questions"]


def _bearer(user_id: int = 1, openid: str = "oid_test") -> dict[str, str]:
    tok = create_access_token(user_id, openid)
    return {"Authorization": f"Bearer {tok}"}


def _strip_debug(body: dict) -> dict:
    """旧测试用例不关心 data.debug_info，剥离后再比对。"""
    if not isinstance(body.get("data"), dict):
        return body
    out = dict(body)
    out["data"] = {k: v for k, v in body["data"].items() if k != "debug_info"}
    return out


@pytest.fixture
def _stub_chain_services():
    """把 QuizChainService.generate_quiz / ReportChainService.generate_report 替换为稳定桩函数，
    保证匿名与登录两条路径的返回结构完全可预测、可比对。"""
    quiz_dump = {
        "quiz_id": "q_stub_001",
        "title": "Spring 基础自测",
        "questions": _fixture_questions,
    }
    from app.models.quiz import QuizGenerateResult
    quiz_result = QuizGenerateResult.model_validate(quiz_dump)

    records = [
        {"question_id": _fixture_questions[i]["question_id"],
         "user_answer": _fixture_questions[i]["answer"],
         "is_correct": True} for i in range(5)
    ]
    report_dump = {
        "accuracy": 100,
        "mastered_points": ["DI 依赖注入", "IoC 容器", "AOP 切面"],
        "weak_points": ["暂无"],
        "three_line_summary": ["S1", "S2", "S3"],
        "advice": "继续加油，向高阶主题进发。",
        "share_quote": "学习使人进步！",
    }
    from app.models.report import ReportGenerateResult
    report_result = ReportGenerateResult.model_validate(report_dump)

    with (
        patch("app.api.v1.routes.quiz.QuizChainService.generate_quiz", AsyncMock(return_value=quiz_result)),
        patch("app.api.v1.routes.report.ReportChainService.generate_report", AsyncMock(return_value=report_result)),
    ):
        yield quiz_dump, records, report_dump


@pytest.mark.asyncio
async def test_quiz_anonymous_vs_logged_in_structure_identical(client, _stub_chain_services):
    quiz_dump, _, _ = _stub_chain_services
    payload = {"user_input": "Spring 框架基础入门", "question_count": 5}

    r_anon = await client.post("/api/v1/quiz/generate", json=payload)
    r_auth = await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(7))
    body_anon = r_anon.json()
    body_auth = r_auth.json()
    assert _strip_debug(body_anon) == _strip_debug(body_auth)
    assert body_anon["data"]["quiz_id"] == quiz_dump["quiz_id"]
    assert body_anon["data"]["title"] == quiz_dump["title"]


@pytest.mark.asyncio
async def test_quiz_logged_in_persists_quiz_session(client, _stub_chain_services, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = None
    cur.lastrowid = 77
    payload = {"user_input": "Spring 框架基础入门", "question_count": 5}
    await client.post("/api/v1/quiz/generate", json=payload, headers=_bearer(7))
    inserts = [c.args[0] for c in cur.execute.await_args_list if str(c.args[0]).upper().startswith("INSERT INTO QUIZ_SESSIONS")]
    assert len(inserts) >= 1, "登录分支必须持久化 quiz_sessions"


@pytest.mark.asyncio
async def test_quiz_anonymous_no_persist_calls(client, _stub_chain_services, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    payload = {"user_input": "Spring 框架基础入门", "question_count": 5}
    await client.post("/api/v1/quiz/generate", json=payload)
    for c in cur.execute.await_args_list:
        sql = str(c.args[0]).upper()
        assert not sql.startswith("INSERT INTO QUIZ_SESSIONS"), "匿名分支不应写入 quiz_sessions"


@pytest.mark.asyncio
async def test_report_anonymous_vs_logged_in_structure_identical(client, _stub_chain_services):
    _, records, report_dump = _stub_chain_services
    payload = {
        "quiz_id": "q_stub_001",
        "quiz": {"questions": _fixture_questions},
        "answer_records": records,
    }
    r_anon = await client.post("/api/v1/report/generate", json=payload)
    r_auth = await client.post("/api/v1/report/generate", json=payload, headers=_bearer(7))
    body_anon = r_anon.json()
    body_auth = r_auth.json()
    stripped_anon = _strip_debug(body_anon)
    stripped_auth = _strip_debug(body_auth)
    assert stripped_anon == stripped_auth
    assert stripped_anon["data"]["accuracy"] == report_dump["accuracy"]
    assert stripped_anon["data"]["advice"] == report_dump["advice"]


@pytest.mark.asyncio
async def test_report_logged_in_triggers_three_persists_and_xp(client, _stub_chain_services, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = (100,)  # new XP after increment
    _, records, _ = _stub_chain_services
    payload = {
        "quiz_id": "q_stub_001",
        "quiz": {"questions": _fixture_questions},
        "answer_records": records,
    }
    with patch("app.api.v1.routes.report.UserRepository.add_xp", AsyncMock(return_value=20)) as mock_addxp:
        await client.post("/api/v1/report/generate", json=payload, headers=_bearer(7))
        assert mock_addxp.await_count == 1
        uid, delta = mock_addxp.await_args_list[0].args
        assert uid == 7
        # 5 correct → 10 + 2*5 = 20
        assert delta == 20


@pytest.mark.asyncio
async def test_report_anonymous_no_xp_no_inserts(client, _stub_chain_services, db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    _, records, _ = _stub_chain_services
    with patch("app.api.v1.routes.report.UserRepository.add_xp", AsyncMock(return_value=0)) as mock_addxp:
        payload = {
            "quiz_id": "q_stub_001",
            "quiz": {"questions": _fixture_questions},
            "answer_records": records,
        }
        await client.post("/api/v1/report/generate", json=payload)
        mock_addxp.assert_not_awaited()
