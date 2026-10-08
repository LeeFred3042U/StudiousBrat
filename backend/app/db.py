"""asyncpg pool access plus the pending-write replay queue.

Every DB helper wraps its exception in DatabaseError so callers can implement
the error-handling table without knowing asyncpg details. Failed writes are
queued (in-process) and replayed on the next action; the frontend also
keeps a localStorage write-through cache.

Connection resilience: some asyncpg/OpenSSL builds reject Neon's
`channel_binding=require` parameter. On failure the pool is retried with
`channel_binding` (and then `sslmode`) stripped from the URL. init() never
raises - if no variant connects, the app still boots and serves reads from
the client-side cache while writes queue for later.
"""
import re
from typing import Any

import asyncpg

from .config import settings


class DatabaseError(Exception):
    pass


_pool: asyncpg.Pool | None = None

# Pending writes: ordered list of (sql, args). Replayed on the next action.
_pending: list[tuple[str, tuple]] = []


def _fallback_urls(url: str) -> list[str]:
    """The URL as given, then progressively simplified variants."""
    urls = [url]
    stripped = re.sub(r"channel_binding=[^&]*", "", url)
    stripped = stripped.replace("?&", "?").replace("&&", "&").rstrip("?&")
    if stripped not in urls:
        urls.append(stripped)
    no_sslmode = re.sub(r"sslmode=[^&]*", "", stripped)
    no_sslmode = no_sslmode.replace("?&", "?").replace("&&", "&").rstrip("?&")
    if no_sslmode not in urls:
        urls.append(no_sslmode)
    return urls


async def init() -> None:
    """Create the pool; never crash the app if Neon is unreachable."""
    global _pool
    if _pool is not None:
        return
    last_error = "no connection string"
    for url in _fallback_urls(settings.database_url):
        try:
            _pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
            return
        except Exception as e:  # bad connection string, DNS failure, TLS, ...
            last_error = str(e)
    _pool = None
    print(f"WARNING: Neon pool not initialized ({last_error}). "
          "Reads will fail over to the client cache; writes are queued.")


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _with_pool(fn):
    if _pool is None:
        raise DatabaseError("pool is not initialized")
    try:
        async with _pool.acquire() as conn:
            return await fn(conn)
    except DatabaseError:
        raise
    except Exception as e:
        raise DatabaseError(str(e))


async def execute(sql: str, *args: Any) -> str:
    return await _with_pool(lambda conn: conn.execute(sql, *args))


async def fetch(sql: str, *args: Any) -> list[asyncpg.Record]:
    return await _with_pool(lambda conn: conn.fetch(sql, *args))


async def fetchrow(sql: str, *args: Any) -> asyncpg.Record | None:
    return await _with_pool(lambda conn: conn.fetchrow(sql, *args))


async def fetchval(sql: str, *args: Any) -> Any:
    return await _with_pool(lambda conn: conn.fetchval(sql, *args))


def queue_write(sql: str, args: tuple) -> None:
    """Queue a failed write for replay on the next user action."""
    _pending.append((sql, tuple(args)))


async def flush_pending() -> int:
    """Replay queued writes; ones that fail again stay queued."""
    global _pending
    remaining: list[tuple[str, tuple]] = []
    flushed = 0
    for sql, args in _pending:
        try:
            await execute(sql, *args)
            flushed += 1
        except DatabaseError:
            remaining.append((sql, args))
    _pending = remaining
    return flushed
