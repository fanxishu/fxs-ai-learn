from __future__ import annotations

import logging
from typing import Optional

import aiomysql
from aiomysql import Pool

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[Pool] = None


async def create_db_pool() -> Pool:
    global _pool
    if _pool is not None:
        return _pool
    logger.info(
        "Creating MySQL pool | host=%s port=%s user=%s db=%s",
        settings.DB_HOST, settings.DB_PORT, settings.DB_USER, settings.DB_NAME,
    )
    _pool = await aiomysql.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        db=settings.DB_NAME,
        charset="utf8mb4",
        autocommit=False,
        minsize=2,
        maxsize=20,
        connect_timeout=10,
    )
    logger.info("MySQL pool created")
    return _pool


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call create_db_pool first.")
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is None:
        return
    _pool.close()
    await _pool.wait_closed()
    _pool = None
    logger.info("MySQL pool closed")


_CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    openid VARCHAR(64) NOT NULL UNIQUE,
    nickname VARCHAR(100) NOT NULL DEFAULT '学习者',
    avatar_url VARCHAR(500) NOT NULL DEFAULT '',
    total_xp INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_total_xp (total_xp),
    INDEX idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_QUIZ_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    quiz_id VARCHAR(64) NOT NULL UNIQUE,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT '',
    summary TEXT NULL,
    user_input TEXT NULL,
    questions_json JSON NULL,
    question_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_quiz_sessions_user_id (user_id),
    INDEX idx_quiz_sessions_created_at (created_at),
    CONSTRAINT fk_quiz_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_ANSWER_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS answer_records (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    quiz_id VARCHAR(64) NOT NULL UNIQUE,
    user_id BIGINT UNSIGNED NOT NULL,
    records_json JSON NULL,
    total_questions INT NOT NULL DEFAULT 0,
    correct_count INT NOT NULL DEFAULT 0,
    accuracy DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_answer_records_user_id (user_id),
    INDEX idx_answer_records_created_at (created_at),
    CONSTRAINT fk_answer_records_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_answer_records_quiz FOREIGN KEY (quiz_id) REFERENCES quiz_sessions(quiz_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_REPORTS_SQL = """
CREATE TABLE IF NOT EXISTS reports (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    quiz_id VARCHAR(64) NOT NULL UNIQUE,
    user_id BIGINT UNSIGNED NOT NULL,
    report_json JSON NULL,
    accuracy DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    total_xp INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reports_user_id (user_id),
    INDEX idx_reports_created_at (created_at),
    CONSTRAINT fk_reports_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_quiz FOREIGN KEY (quiz_id) REFERENCES quiz_sessions(quiz_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_CREATE_QUIZ_TASKS_SQL = """
CREATE TABLE IF NOT EXISTS quiz_generation_tasks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    user_id BIGINT UNSIGNED NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    user_input TEXT NOT NULL,
    question_count INT NOT NULL DEFAULT 0,
    result_json JSON NULL,
    error_message VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    finished_at DATETIME NULL,
    INDEX idx_quiz_tasks_user_id (user_id),
    INDEX idx_quiz_tasks_status (status),
    INDEX idx_quiz_tasks_created_at (created_at),
    CONSTRAINT fk_quiz_tasks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


async def create_tables_if_not_exists() -> None:
    pool = get_pool()
    statements = [
        ("users", _CREATE_USERS_SQL),
        ("quiz_sessions", _CREATE_QUIZ_SESSIONS_SQL),
        ("answer_records", _CREATE_ANSWER_RECORDS_SQL),
        ("reports", _CREATE_REPORTS_SQL),
        ("quiz_generation_tasks", _CREATE_QUIZ_TASKS_SQL),
    ]
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for name, sql in statements:
                logger.info("Ensuring table exists: %s", name)
                await cur.execute(sql)

            logger.info("Applying schema migrations (ADD COLUMN if missing)...")
            migrations = [
                ("quiz_sessions", "question_count",
                 "ALTER TABLE quiz_sessions ADD COLUMN question_count INT NOT NULL DEFAULT 0 AFTER questions_json"),
                ("quiz_sessions", "total_xp",
                 "ALTER TABLE quiz_sessions ADD COLUMN total_xp INT NOT NULL DEFAULT 0 AFTER question_count"),
            ]
            for table, column, ddl in migrations:
                await cur.execute(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                    (table, column),
                )
                row = await cur.fetchone()
                c = int(row[0]) if row and row[0] is not None else 0
                if c == 0:
                    logger.info("Adding missing column %s.%s", table, column)
                    await cur.execute(ddl)
            await conn.commit()
    logger.info("All tables ensured + migrations applied")
