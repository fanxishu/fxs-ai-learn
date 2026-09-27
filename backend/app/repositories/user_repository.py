from __future__ import annotations

import logging
from typing import Any, Optional

from app.core.db import get_pool

logger = logging.getLogger(__name__)


class UserRepository:
    TABLE = "users"

    @classmethod
    async def get_by_openid(cls, openid: str) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            # Pooled read connections must not retain repeatable-read snapshots.
            await conn.rollback()
            async with conn.cursor() as cur:
                sql = f"SELECT id, openid, nickname, avatar_url, total_xp, created_at, updated_at FROM {cls.TABLE} WHERE openid = %s LIMIT 1"
                await cur.execute(sql, (openid,))
                row = await cur.fetchone()
            await conn.rollback()
        return cls._row_to_dict(row) if row else None

    @classmethod
    async def create(cls, openid: str, nickname: str = "学习者", avatar_url: str = "") -> int:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = f"INSERT INTO {cls.TABLE} (openid, nickname, avatar_url, total_xp) VALUES (%s, %s, %s, 0)"
                await cur.execute(sql, (openid, nickname, avatar_url))
                new_id = cur.lastrowid
                await conn.commit()
        logger.info("User created id=%s openid=%s", new_id, openid)
        return int(new_id)

    @classmethod
    async def get_by_id(cls, user_id: int) -> Optional[dict]:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.rollback()
            async with conn.cursor() as cur:
                sql = f"SELECT id, openid, nickname, avatar_url, total_xp, created_at, updated_at FROM {cls.TABLE} WHERE id = %s LIMIT 1"
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()
            await conn.rollback()
        return cls._row_to_dict(row) if row else None

    @classmethod
    async def update_profile(cls, user_id: int, nickname: Optional[str], avatar_url: Optional[str]) -> None:
        fields: list[str] = []
        args: list[Any] = []
        if nickname is not None:
            fields.append("nickname = %s")
            args.append(nickname)
        if avatar_url is not None:
            fields.append("avatar_url = %s")
            args.append(avatar_url)
        if not fields:
            return
        args.append(user_id)
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = f"UPDATE {cls.TABLE} SET {', '.join(fields)} WHERE id = %s"
                await cur.execute(sql, tuple(args))
                await conn.commit()

    @classmethod
    async def add_xp(cls, user_id: int, delta: int) -> int:
        """原子 XP 累加：UPDATE SET total_xp = total_xp + %s WHERE id = %s。
        返回更新后的最新 total_xp（需要额外 SELECT，或在同一事务执行）。"""
        if delta <= 0:
            current = await cls.get_by_id(user_id)
            return int(current["total_xp"]) if current else 0
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"UPDATE {cls.TABLE} SET total_xp = total_xp + %s WHERE id = %s", (delta, user_id))
                await cur.execute(f"SELECT total_xp FROM {cls.TABLE} WHERE id = %s LIMIT 1", (user_id,))
                row = await cur.fetchone()
                await conn.commit()
        return int(row[0]) if row else 0

    @classmethod
    async def get_profile_stats(cls, user_id: int) -> dict:
        """聚合 profile 统计：quiz_count / correct_count / total_questions_sum / average_accuracy。
        平均正确率口径：sum(correct_count) / sum(total_questions) * 100，四舍五入取整。sum=0 时 0。"""
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = (
                    "SELECT COUNT(*) AS quiz_count, "
                    "COALESCE(SUM(correct_count),0) AS correct_count, "
                    "COALESCE(SUM(total_questions),0) AS total_questions_sum "
                    "FROM answer_records WHERE user_id = %s"
                )
                await cur.execute(sql, (user_id,))
                row = await cur.fetchone()
        quiz_count = int(row[0]) if row else 0
        correct_count = int(row[1]) if row else 0
        total_q = int(row[2]) if row else 0
        if total_q > 0:
            avg_acc = round(correct_count * 100 / total_q)
        else:
            avg_acc = 0
        return {
            "quiz_count": quiz_count,
            "correct_count": correct_count,
            "total_questions_sum": total_q,
            "average_accuracy": avg_acc,
        }

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        return {
            "id": int(row[0]),
            "openid": row[1],
            "nickname": row[2],
            "avatar_url": row[3] or "",
            "total_xp": int(row[4]),
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
        }
