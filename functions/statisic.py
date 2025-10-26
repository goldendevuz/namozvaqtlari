from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

try:
    from aiogram.types import User, Message
except Exception:
    User = object
    Message = object

ADMIN_IDS = set()


def _load_admin_ids():
    if not ADMIN_IDS:
        admin1 = os.getenv("ADMIN1")
        admin2 = os.getenv("ADMIN2")
        for _v in (admin1, admin2):
            try:
                if _v:
                    ADMIN_IDS.add(int(_v))
            except Exception:
                pass


def _db_path() -> str:
    root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "bot.sqlite3")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                language_code TEXT,
                is_bot INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                date_joined INTEGER,
                last_seen INTEGER,
                source TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_or_update_user(user, is_admin: bool = False, source: Optional[str] = None) -> None:
    now = int(time.time())
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO users (id, first_name, last_name, username, language_code, is_bot, is_admin, date_joined, last_seen, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                username=excluded.username,
                language_code=excluded.language_code,
                is_bot=excluded.is_bot,
                is_admin=max(users.is_admin, excluded.is_admin),
                last_seen=excluded.last_seen,
                source=COALESCE(users.source, excluded.source)
            """,
            (
                int(getattr(user, "id", 0)),
                getattr(user, "first_name", None),
                getattr(user, "last_name", None),
                getattr(user, "username", None),
                getattr(user, "language_code", None),
                1 if getattr(user, "is_bot", False) else 0,
                1 if is_admin else 0,
                now,
                now,
                source,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_stats() -> Dict[str, Any]:
    now = int(time.time())
    midnight = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    last24 = now - 24 * 3600

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM users WHERE is_admin=1")
        total_admins = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM users WHERE date_joined >= ? AND is_admin=0", (midnight,))
        joined_today = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen >= ? AND is_admin=0", (last24,))
        active_24h = cur.fetchone()[0] or 0

        return {
            "total_users": total_users,
            "total_admins": total_admins,
            "joined_today": joined_today,
            "active_24h": active_24h,
        }
    finally:
        conn.close()


def format_stats(stats: Dict[str, Any]) -> str:
    return (
        "📊 Statistika\n"
        "=============================\n"
        f"👥 Umumiy foydalanuvchilar: {stats.get('total_users', 0)}\n"
        f"🛡 Administratorlar: {stats.get('total_admins', 0)}\n"
        f"🆕 Bugun qo'shilgan: {stats.get('joined_today', 0)}\n"
        f"⚡ Oxirgi 24 soatda faol: {stats.get('active_24h', 0)}\n"
    )

async def handle_stats(message) -> None:
    _load_admin_ids()
    user_id = int(getattr(message.from_user, "id", 0) or 0)
    print(f"[DEBUG] User ID: {user_id}, ADMIN_IDS: {ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ushbu buyruq faqat adminlar uchun.")
        return

    try:
        stats = await asyncio.to_thread(get_stats)
        text = format_stats(stats)
        print(f"[DEBUG] Sending stats: {text}")
        await message.answer(text)
    except Exception as e:
        print(f"[ERROR] Stats error: {e}")
        await message.answer("❗ Statistika olishda xatolik yuz berdi.")


__all__ = [
    "init_db",
    "add_or_update_user",
    "get_stats",
    "format_stats",
    "handle_stats",
]
