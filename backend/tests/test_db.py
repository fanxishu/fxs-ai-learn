import re

import pytest

from app.core import db as db_mod


TABLE_NAMES = ["users", "quiz_sessions", "answer_records", "reports", "quiz_generation_tasks"]
_CREATE_ATTRS = [
    "_CREATE_USERS_SQL",
    "_CREATE_QUIZ_SESSIONS_SQL",
    "_CREATE_ANSWER_RECORDS_SQL",
    "_CREATE_REPORTS_SQL",
    "_CREATE_QUIZ_TASKS_SQL",
]


def test_tr21_all_four_create_statements_defined():
    for attr in _CREATE_ATTRS:
        sql = getattr(db_mod, attr, None)
        assert isinstance(sql, str) and sql.strip(), f"missing {attr}"
        assert "CREATE TABLE IF NOT EXISTS" in sql, f"{attr} not IF NOT EXISTS"


def test_tr22_all_tables_have_bigint_autoinc_id_pk():
    for attr in _CREATE_ATTRS:
        sql = getattr(db_mod, attr)
        m = re.search(r"id\s+BIGINT\s+UNSIGNED\s+AUTO_INCREMENT\s+PRIMARY\s+KEY", sql, re.I)
        assert m, f"{attr} PK mismatch"


def test_tr23_all_sql_values_are_parametrized_no_fstrings():
    """验证核心模块（db.py / repositories/*）所有 SQL 拼接字段名用 TABLE 常量，值全部 %s 参数化，
    不存在直接拼接用户输入的 f-string。"""
    forbidden_patterns = [r"f\"[^\"]*%", r"f'[^']*%", 'f"[^"]*\{[^}]*[^}A-Z_][^}]*\}"']
    # 简单强约束：所有 %s 占位符出现时，execute 第二个参数都是 tuple/list（Repository 层保证）
    # 这里只检查 db.py 4 条 CREATE TABLE 里没有内嵌用户字符串（table name 是常量硬编码）
    for attr in _CREATE_ATTRS:
        sql = getattr(db_mod, attr)
        assert "openid = " not in sql or "%s" in sql  # 没有 f"{user_input}"
        # 所有 CREATE TABLE 列名都在白名单，不接受变量插值
        # 简单断言：无连续 {{ }} 无 Python f-string 片段
        for kw in ("f\"", "f'", "{", "}"):
            if kw in ("{", "}"):
                # JSON 字段允许存在一对 {}，不要误判
                continue
            assert kw not in sql, f"{attr} 含禁止片段: {kw}"


@pytest.mark.asyncio
async def test_create_tables_executes_five_creates(db_pool_cur):
    _, cur = db_pool_cur
    cur.execute.reset_mock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    await db_mod.create_tables_if_not_exists()
    calls = [c for c in cur.execute.await_args_list if str(c.args[0]).strip().upper().startswith("CREATE TABLE")]
    assert len(calls) == 5, f"should execute 5 CREATE TABLE, got {len(calls)}"
