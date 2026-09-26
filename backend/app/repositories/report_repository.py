from __future__ import annotations

import json
import logging
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
    ) -> None:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    f"INSERT INTO {cls.TABLE} "
                    "(quiz_id, user_id, report_json) VALUES (%s, %s, %s)"
                )
                r_json = json.dumps(report_json, ensure_ascii=False) if report_json is not None else None
                await cur.execute(sql, (quiz_id, user_id, r_json))
                await conn.commit()
        logger.info("Report persisted quiz_id=%s user_id=%s", quiz_id, user_id)

    @classmethod
    async def get_by_quiz_id_for_user(cls, quiz_id: str, user_id: int) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    "SELECT id, quiz_id, user_id, report_json, created_at "
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
        return {
            "id": int(row[0]),
            "quiz_id": row[1],
            "user_id": int(row[2]),
            "report": report,
            "created_at": row[4].isoformat() if row[4] else None,
        }
