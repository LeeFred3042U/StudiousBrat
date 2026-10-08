"""Apply migrations/001_init.sql to Neon without needing psql.

Usage (from backend/):
    python migrate.py

Idempotent: if the student_profiles table already exists, it does nothing.
"""
import asyncio
import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
SQL_FILE = HERE.parent / "migrations" / "001_init.sql"


def _fallback_urls(url: str) -> list[str]:
    urls = [url]
    stripped = re.sub(r"channel_binding=[^&]*", "", url)
    stripped = stripped.replace("?&", "?").replace("&&", "&").rstrip("?&")
    if stripped not in urls:
        urls.append(stripped)
    return urls


async def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set (check backend/.env)")
    if not SQL_FILE.exists():
        raise SystemExit(f"Migration file not found: {SQL_FILE}")

    conn = None
    last_error = None
    for candidate in _fallback_urls(url):
        try:
            conn = await asyncpg.connect(candidate)
            break
        except Exception as e:
            last_error = e
    if conn is None:
        raise SystemExit(f"Could not connect to the database: {last_error}")

    try:
        exists = await conn.fetchval("SELECT to_regclass('public.student_profiles')")
        if exists:
            print("Migration already applied (student_profiles exists) - skipping.")
            return
        await conn.execute(SQL_FILE.read_text(encoding="utf-8"))
        print("Migration applied: 001_init.sql")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
