from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.db import get_pool

logger = logging.getLogger(__name__)


class QuizSessionRepository:
    TABLE = "quiz_sessions"

    @classmethod
    async def create(
        cls,
        quiz_id: str,
        user_id: int,
        title: str,
        summary: Optional[str],
        user_input: Optional[str],
        questions_json: Any,
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"INSERT INTO {cls.TABLE} "
                    "(quiz_id, user_id, title, summary, user_input, questions_json) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                q_json = json.dumps(questions_json, ensure_ascii=False) if questions_json is not None else None
                await cur.execute(sql, (quiz_id, user_id, title or "", summary, user_input, q_json))
                await conn.commit()
        logger.info("QuizSession persisted quiz_id=%s user_id=%s", quiz_id, user_id)

    @classmethod
    async def get_by_quiz_id_for_user(cls, quiz_id: str, user_id: int) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    "SELECT id, quiz_id, user_id, title, summary, user_input, questions_json, created_at "
                    f"FROM {cls.TABLE} WHERE quiz_id = %s AND user_id = %s LIMIT 1"
                )
                await cur.execute(sql, (quiz_id, user_id))
                row = await cur.fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    async def list_by_user(
        cls,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT COUNT(*) FROM {cls.TABLE} WHERE user_id = %s", (user_id,))
                total_row = await cur.fetchone()
                total = int(total_row[0]) if total_row else 0
                sql = (
                    "SELECT qs.quiz_id, qs.title, qs.created_at, "
                    "COALESCE(ar.total_questions,0) AS question_count, "
                    "COALESCE(ar.accuracy,0) AS accuracy, "
                    "COALESCE(r.total_xp,0) AS total_xp, "
                    "COALESCE(ar.correct_count,0) AS correct_count "
                    f"FROM {cls.TABLE} qs "
                    "LEFT JOIN answer_records ar ON qs.quiz_id = ar.quiz_id AND ar.user_id = qs.user_id "
                    "LEFT JOIN reports r ON qs.quiz_id = r.quiz_id AND r.user_id = qs.user_id "
                    "WHERE qs.user_id = %s "
                    "ORDER BY qs.created_at DESC, qs.id DESC "
                    "LIMIT %s OFFSET %s"
                )
                await cur.execute(sql, (user_id, page_size, offset))
                rows = await cur.fetchall()
        items: list[dict] = []
        for r in rows:
            acc_raw = r[4]
            try:
                acc = round(float(acc_raw or 0))
            except Exception:
                acc = 0
            items.append({
                "quiz_id": r[0],
                "title": r[1] or "",
                "created_at": r[2].isoformat() if r[2] else None,
                "question_count": int(r[3] or 0),
                "accuracy": acc,
                "total_xp": int(r[5] or 0),
                "correct_count": int(r[6] or 0),
            })
        return items, total

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        q_json = row[6]
        if isinstance(q_json, str):
            try:
                questions = json.loads(q_json)
            except Exception:
                questions = None
        else:
            questions = q_json
        return {
            "id": int(row[0]),
            "quiz_id": row[1],
            "user_id": int(row[2]),
            "title": row[3] or "",
            "summary": row[4],
            "user_input": row[5],
            "questions": questions,
            "created_at": row[7].isoformat() if row[7] else None,
        }
