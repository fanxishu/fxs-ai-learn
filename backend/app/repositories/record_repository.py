from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Optional

from app.core.db import get_pool

logger = logging.getLogger(__name__)


class AnswerRecordRepository:
    TABLE = "answer_records"

    @classmethod
    async def create(
        cls,
        quiz_id: str,
        user_id: int,
        records_json: Any,
        total_questions: int,
        correct_count: int,
        accuracy: float,
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"INSERT INTO {cls.TABLE} "
                    "(quiz_id, user_id, records_json, total_questions, correct_count, accuracy) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                r_json = json.dumps(records_json, ensure_ascii=False) if records_json is not None else None
                acc_decimal = Decimal(str(round(float(accuracy or 0.0), 2)))
                await cur.execute(
                    sql,
                    (quiz_id, user_id, r_json, int(total_questions), int(correct_count), acc_decimal),
                )
                await conn.commit()
        logger.info(
            "AnswerRecord persisted quiz_id=%s user_id=%s total=%s correct=%s acc=%s",
            quiz_id, user_id, total_questions, correct_count, accuracy,
        )

    @classmethod
    async def get_by_quiz_id_for_user(cls, quiz_id: str, user_id: int) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    "SELECT id, quiz_id, user_id, records_json, total_questions, correct_count, accuracy, created_at "
                    f"FROM {cls.TABLE} WHERE quiz_id = %s AND user_id = %s LIMIT 1"
                )
                await cur.execute(sql, (quiz_id, user_id))
                row = await cur.fetchone()
        return cls._row_to_dict(row) if row else None

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        r_json = row[3]
        if isinstance(r_json, str):
            try:
                records = json.loads(r_json)
            except Exception:
                records = None
        else:
            records = r_json
        try:
            acc = round(float(row[6] or 0))
        except Exception:
            acc = 0
        return {
            "id": int(row[0]),
            "quiz_id": row[1],
            "user_id": int(row[2]),
            "records": records,
            "total_questions": int(row[4]),
            "correct_count": int(row[5]),
            "accuracy": acc,
            "created_at": row[7].isoformat() if row[7] else None,
        }
