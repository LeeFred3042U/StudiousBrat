"""Standalone check that the Neon POOLED connection string works.

Usage (from backend/):
    python verify_db.py

Reads DATABASE_URL from the environment or backend/.env.
If the connection fails with `channel_binding=require` (some asyncpg/OpenSSL
builds reject it), the script retries with that parameter stripped.
"""
import asyncio
import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


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
        raise SystemExit("DATABASE_URL is not set")
    if "-pooler" not in url:
        print("WARNING: this does not look like the pooled (PgBouncer) string.")

    conn = None
    last_error = None
    for candidate in _fallback_urls(url):
        try:
            conn = await asyncpg.connect(candidate)
            break
        except Exception as e:
            last_error = e
    if conn is None:
        raise SystemExit(f"Could not connect: {last_error}")

    try:
        version = await conn.fetchval("SELECT version()")
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        print("Connected:", version.split(",")[0])
        print("Tables:", ", ".join(t["table_name"] for t in tables) or "(none yet)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
