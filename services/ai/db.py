"""Thin asyncpg pool with per-request tenant scoping.

Every tenant-scoped query must run inside `tenant_conn(org_id)` so that the
Postgres RLS policies (see prisma/migrations/001_*) filter rows automatically.
"""

import os
import asyncpg
from contextlib import asynccontextmanager

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"], min_size=2, max_size=10
    )


async def close_pool() -> None:
    if _pool:
        await _pool.close()


@asynccontextmanager
async def tenant_conn(org_id: str):
    """Acquire a connection with `app.current_org` set for RLS isolation."""
    assert _pool is not None, "call init_pool() at startup"
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL app.current_org = $1", org_id)
            yield conn
