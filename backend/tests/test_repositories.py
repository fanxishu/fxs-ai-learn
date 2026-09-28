from datetime import datetime
from decimal import Decimal

import pytest

from app.repositories import (
    UserRepository,
    QuizSessionRepository,
    QuizTaskRepository,
    AnswerRecordRepository,
    ReportRepository,
)


def _rows_by_sql(cur, startswith: str):
    return [c.args for c in cur.execute.await_args_list if str(c.args[0]).upper().startswith(startswith.upper())]


@pytest.mark.asyncio
async def test_tr_user_add_xp_uses_atomic_increment(db_pool_cur):
    """XP 必须是 UPDATE SET total_xp = total_xp + %s 的原子语句，不能读-改-写。"""
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = (35,)
    await UserRepository.add_xp(7, 12)
    calls = cur.execute.await_args_list
    first_sql = str(calls[0].args[0]).strip()
    normalized = first_sql.replace("`", " ").lower()
    assert "update users set total_xp = total_xp + %s" in normalized, first_sql
    # SELECT 读取新值然后返回
    sel_sql = str(calls[1].args[0]).strip().lower().replace("`", " ")
    assert "select total_xp from users" in sel_sql
    # 值校验
    assert calls[0].args[1][0] == 12
    assert calls[0].args[1][1] == 7


@pytest.mark.asyncio
async def test_tr_user_profile_stats_aggregation_formula(db_pool_cur):
    """平均正确率 = sum(correct_count) / sum(total_questions) * 100，四舍五入取整。"""
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    # quiz_count=3, correct_count=20, total_questions=27 → 20/27≈74.07% → 74
    cur.fetchone.return_value = (3, 20, 27)
    stats = await UserRepository.get_profile_stats(1)
    assert stats["quiz_count"] == 3
    assert stats["correct_count"] == 20
    assert stats["total_questions_sum"] == 27
    assert stats["average_accuracy"] == 74


@pytest.mark.asyncio
async def test_tr_user_profile_stats_zero_total_returns_0(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = (0, 0, 0)
    stats = await UserRepository.get_profile_stats(1)
    assert stats["average_accuracy"] == 0


@pytest.mark.asyncio
async def test_tr_user_get_by_openid_uses_unique_index(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = (
        99, "oid_x", "学习者", "", 15,
        datetime(2026, 3, 1, 10, 0, 0), datetime(2026, 3, 2, 10, 0, 0),
    )
    user = await UserRepository.get_by_openid("oid_x")
    assert user["id"] == 99 and user["nickname"] == "学习者"
    assert "WHERE openid = %s LIMIT 1" in str(cur.execute.await_args_list[0].args[0])
    assert cur.execute.await_args_list[0].args[1] == ("oid_x",)


@pytest.mark.asyncio
async def test_tr_quiz_create_uses_all_params(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    await QuizSessionRepository.create(
        quiz_id="q1", user_id=5, title="T", summary="S",
        user_input="Spring 基础", questions_json=[{"qid": "q_1"}],
    )
    args = cur.execute.await_args_list[0].args
    assert str(args[0]).upper().startswith("INSERT INTO QUIZ_SESSIONS")
    vals = args[1]
    assert vals[0] == "q1" and vals[1] == 5 and vals[2] == "T" and vals[5] is not None
    # JSON 字符串应该包含 q_1
    assert "q_1" in str(vals[5])


@pytest.mark.asyncio
async def test_tr_record_create_stores_correct_decimal_accuracy(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    await AnswerRecordRepository.create(
        quiz_id="q1", user_id=5, records_json=[{"a": 1}],
        total_questions=5, correct_count=4, accuracy=80.0,
    )
    args = cur.execute.await_args_list[0].args
    normalized_sql = args[0].lower().replace("`", " ")
    assert "insert into answer_records" in normalized_sql
    vals = args[1]
    # 第 5 个值 accuracy 必须是 Decimal(80.00)
    assert isinstance(vals[5], Decimal)
    assert vals[5] == Decimal("80.00")
    assert vals[3] == 5 and vals[4] == 4


@pytest.mark.asyncio
async def test_tr_report_create_json_serialized(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    report_obj = {"accuracy": 80, "advice": "继续加油", "three_line_summary": ["a", "b", "c"]}
    await ReportRepository.create(quiz_id="q1", user_id=5, report_json=report_obj)
    args = cur.execute.await_args_list[0].args
    normalized_sql = args[0].lower().replace("`", " ")
    assert "insert into reports" in normalized_sql
    stored_report = args[1][2]
    assert isinstance(stored_report, str) and "继续加油" in stored_report


@pytest.mark.asyncio
async def test_tr_quiz_task_create_uses_all_params(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    await QuizTaskRepository.create(
        task_id="qtask-1",
        user_id=8,
        user_input="Harness Engineering",
        question_count=5,
    )
    args = cur.execute.await_args_list[0].args
    assert str(args[0]).upper().startswith("INSERT INTO QUIZ_GENERATION_TASKS")
    vals = args[1]
    assert vals == ("qtask-1", 8, "pending", "Harness Engineering", 5)


@pytest.mark.asyncio
async def test_tr_quiz_task_mark_succeeded_serializes_json(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    await QuizTaskRepository.mark_succeeded(
        task_id="qtask-2",
        user_id=8,
        result_json={"quiz_id": "quiz_1", "title": "T"},
    )
    args = cur.execute.await_args_list[0].args
    normalized_sql = args[0].lower().replace("`", " ")
    assert "update quiz_generation_tasks" in normalized_sql
    assert args[1][0] == "succeeded"
    assert "\"quiz_id\": \"quiz_1\"" in args[1][1]


@pytest.mark.asyncio
async def test_tr_quiz_task_get_by_task_id_for_user_maps_result_json(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = (
        1,
        "qtask-3",
        9,
        "succeeded",
        "Python 新特性",
        4,
        "{\"quiz_id\": \"quiz_9\", \"title\": \"新题目\"}",
        None,
        datetime(2026, 3, 1, 10, 0, 0),
        datetime(2026, 3, 1, 10, 1, 0),
        datetime(2026, 3, 1, 10, 2, 0),
    )
    task = await QuizTaskRepository.get_by_task_id_for_user("qtask-3", 9)
    assert task["task_id"] == "qtask-3"
    assert task["status"] == "succeeded"
    assert task["result_json"]["quiz_id"] == "quiz_9"
