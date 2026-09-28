from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.db import get_pool

logger = logging.getLogger(__name__)


class QuizTaskRepository:
    TABLE = "quiz_generation_tasks"

    @classmethod
    async def create(
        cls,
        task_id: str,
        user_id: int,
        user_input: str,
        question_count: int,
        status: str = "pending",
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"INSERT INTO {cls.TABLE} "
                    "(task_id, user_id, status, user_input, question_count) "
                    "VALUES (%s, %s, %s, %s, %s)"
                )
                await cur.execute(
                    sql,
                    (task_id, int(user_id), status, user_input, int(question_count)),
                )
                await conn.commit()
        logger.info("Quiz task created task_id=%s user_id=%s", task_id, user_id)

    @classmethod
    async def mark_running(cls, task_id: str, user_id: int) -> None:
        await cls._update_status(task_id, user_id, "running")

    @classmethod
    async def mark_succeeded(
        cls,
        task_id: str,
        user_id: int,
        result_json: Any,
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"UPDATE {cls.TABLE} "
                    "SET status = %s, result_json = %s, error_message = NULL, finished_at = CURRENT_TIMESTAMP "
                    "WHERE task_id = %s AND user_id = %s"
                )
                dumped = json.dumps(result_json, ensure_ascii=False)
                await cur.execute(sql, ("succeeded", dumped, task_id, int(user_id)))
                await conn.commit()

    @classmethod
    async def mark_failed(
        cls,
        task_id: str,
        user_id: int,
        error_message: str,
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"UPDATE {cls.TABLE} "
                    "SET status = %s, error_message = %s, finished_at = CURRENT_TIMESTAMP "
                    "WHERE task_id = %s AND user_id = %s"
                )
                await cur.execute(
                    sql,
                    ("failed", error_message[:500], task_id, int(user_id)),
                )
                await conn.commit()

    @classmethod
    async def get_by_task_id_for_user(
        cls,
        task_id: str,
        user_id: int,
    ) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await conn.rollback()
                sql = (
                    "SELECT id, task_id, user_id, status, user_input, question_count, "
                    "result_json, error_message, created_at, updated_at, finished_at "
                    f"FROM {cls.TABLE} WHERE task_id = %s AND user_id = %s LIMIT 1"
                )
                await cur.execute(sql, (task_id, int(user_id)))
                row = await cur.fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    async def _update_status(cls, task_id: str, user_id: int, status: str) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"UPDATE {cls.TABLE} "
                    "SET status = %s, error_message = NULL "
                    "WHERE task_id = %s AND user_id = %s"
                )
                await cur.execute(sql, (status, task_id, int(user_id)))
                await conn.commit()

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        result_raw = row[6]
        if isinstance(result_raw, str):
            try:
                result_json = json.loads(result_raw)
            except Exception:
                result_json = None
        else:
            result_json = result_raw
        return {
            "id": int(row[0]),
            "task_id": row[1],
            "user_id": int(row[2]),
            "status": row[3],
            "user_input": row[4] or "",
            "question_count": int(row[5] or 0),
            "result_json": result_json,
            "error_message": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
            "finished_at": row[10].isoformat() if row[10] else None,
        }
