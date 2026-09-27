from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, Optional

from app.core.db import get_pool

logger = logging.getLogger(__name__)


class ReportRepository:
    TABLE = "reports"

    @classmethod
    async def create(
        cls,
        quiz_id: str,
        user_id: int,
        report_json: Any,
        accuracy: float = 0.0,
        total_xp: int = 0,
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"INSERT INTO {cls.TABLE} "
                    "(quiz_id, user_id, report_json, accuracy, total_xp) "
                    "VALUES (%s, %s, %s, %s, %s)"
                )
                r_json = json.dumps(report_json, ensure_ascii=False) if report_json is not None else None
                acc_decimal = Decimal(str(round(float(accuracy or 0.0), 2)))
                await cur.execute(
                    sql,
                    (quiz_id, user_id, r_json, acc_decimal, int(total_xp or 0)),
                )
                await conn.commit()
        logger.info(
            "Report persisted quiz_id=%s user_id=%s acc=%s xp=%s",
            quiz_id, user_id, accuracy, total_xp,
        )

    @classmethod
    async def get_by_quiz_id_for_user(cls, quiz_id: str, user_id: int) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    "SELECT id, quiz_id, user_id, report_json, accuracy, total_xp, created_at "
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
                report = json.loads(r_json)
            except Exception:
                report = None
        else:
            report = r_json
        try:
            acc = round(float(row[4] or 0))
        except Exception:
            acc = 0
        return {
            "id": int(row[0]),
            "quiz_id": row[1],
            "user_id": int(row[2]),
            "report": report,
            "accuracy": acc,
            "total_xp": int(row[5] or 0),
            "created_at": row[6].isoformat() if row[6] else None,
        }
