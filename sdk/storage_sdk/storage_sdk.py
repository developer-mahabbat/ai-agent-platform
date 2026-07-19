import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from ..base import SDKModule, SDKResult

logger = logging.getLogger(__name__)


class StorageSDK(SDKModule):
    name = "storage"
    version = "1.0.0"

    def __init__(self, context=None):
        super().__init__(context)
        self._conn: Optional[sqlite3.Connection] = None
        self._db_path: str = "mkcode.db"

    async def initialize(self) -> None:
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        logger.info(f"StorageSDK initialized (db: {self._db_path})")

    async def shutdown(self) -> None:
        if self._conn:
            self._conn.close()
        logger.info("StorageSDK shut down")

    async def _create_tables(self) -> None:
        if not self._conn:
            return
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                created_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                title TEXT DEFAULT '',
                model TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT REFERENCES chats(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                type TEXT DEFAULT 'conversation',
                content TEXT NOT NULL,
                summary TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                score REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                path TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                chat_id TEXT REFERENCES chats(id),
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                type TEXT DEFAULT 'code',
                language TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_agent TEXT DEFAULT '',
                result TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                module TEXT DEFAULT '',
                message TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    async def execute(self, sql: str, params: tuple = ()) -> SDKResult:
        if not self._conn:
            return SDKResult.fail("Database not connected")
        try:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return SDKResult.ok({"rowcount": cursor.rowcount, "lastrowid": cursor.lastrowid})
        except Exception as e:
            return SDKResult.fail(str(e))

    async def fetch(self, sql: str, params: tuple = ()) -> SDKResult[list[dict]]:
        if not self._conn:
            return SDKResult.fail("Database not connected")
        try:
            cursor = self._conn.execute(sql, params)
            rows = [dict(row) for row in cursor.fetchall()]
            return SDKResult.ok(rows)
        except Exception as e:
            return SDKResult.fail(str(e))

    async def fetch_one(self, sql: str, params: tuple = ()) -> SDKResult[Optional[dict]]:
        if not self._conn:
            return SDKResult.fail("Database not connected")
        try:
            cursor = self._conn.execute(sql, params)
            row = cursor.fetchone()
            return SDKResult.ok(dict(row) if row else None)
        except Exception as e:
            return SDKResult.fail(str(e))
