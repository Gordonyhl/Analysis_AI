"""Postgres storage utilities.

Owns read/write to Postgres and conversion between agent messages and DB rows.

Functions provided:
- get_async_engine: Build a singleton async engine from settings.
- init_schema: Initialize schema from db/init/001_schema.sql (idempotent).
- get_or_create_thread_by_title / get_or_create_default_thread: Thread management.
- load_recent_messages_for_thread / load_recent_messages_for_default_thread: History loading.
- append_message / append_messages: Persist new messages with next sequential idx.
- count_messages, get_last_index, export_thread: Utilities for sanity checks/debugging.

Note on message shape:
- We return a list of dictionaries shaped like the agent expects, e.g. {"role": "user", "content": "..."}.
- The schema stores role as text and content as JSONB. We persist whatever is in the "content" field as JSON.
- We may need to adjust the shape to perfectly match pydantic-ai's ModelMessage in the future.
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from settings import settings


# ---------- Engine ----------

@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    """Create or return a cached async SQLAlchemy engine using asyncpg."""
    return create_async_engine(settings.resolved_database_url, pool_pre_ping=True)


# ---------- Schema initialization ----------

async def init_schema(engine: Optional[AsyncEngine] = None) -> None:
    """Initialize schema by executing db/init/001_schema.sql.

    Uses IF NOT EXISTS statements in the SQL to remain idempotent.
    """
    engine = engine or get_async_engine()
    sql_path = Path(__file__).parent / "db" / "init" / "001_schema.sql"
    script = sql_path.read_text(encoding="utf-8")

    # Execute each statement separately for driver compatibility
    statements = _split_sql_statements(script)
    async with engine.begin() as conn:
        for stmt in statements:
            await conn.exec_driver_sql(stmt)


def _split_sql_statements(script: str) -> List[str]:
    """Split SQL script into executable statements.

    - Strips full-line and inline '--' comments before splitting
    - Splits on ';' terminators
    - Drops empty statements
    """
    processed_lines: List[str] = []
    for raw_line in script.splitlines():
        # Remove inline comments starting with '--'
        if "--" in raw_line:
            raw_line = raw_line.split("--", 1)[0]
        line = raw_line.strip()
        if not line:
            continue
        processed_lines.append(line)

    joined = "\n".join(processed_lines)
    parts = [p.strip() for p in joined.split(";")]
    return [p for p in parts if p]


# ---------- Threads ----------

async def get_or_create_thread_by_title(title: str, *, engine: Optional[AsyncEngine] = None) -> uuid.UUID:
    """Fetch thread id by title or create one."""
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        existing = await conn.execute(
            text("SELECT id FROM threads WHERE title = :title LIMIT 1"), {"title": title}
        )
        row = existing.first()
        if row is not None:
            return uuid.UUID(str(row[0]))

        thread_id = uuid.uuid4()
        await conn.execute(
            text("INSERT INTO threads (id, title) VALUES (:id, :title)"),
            {"id": str(thread_id), "title": title},
        )
        return thread_id


async def get_or_create_default_thread(*, engine: Optional[AsyncEngine] = None) -> uuid.UUID:
    """Use settings.thread_title to get or create the default thread."""
    return await get_or_create_thread_by_title(settings.thread_title, engine=engine)


# ---------- Messages ----------

def _row_to_agent_message(row: Tuple[Any, Any, Any]) -> Dict[str, Any]:
    role, content_json, _idx = row
    return {"role": role, "content": content_json}


async def load_recent_messages_for_thread(
    thread_id: uuid.UUID, limit: int, *, engine: Optional[AsyncEngine] = None
) -> List[Dict[str, Any]]:
    """Load most recent N messages ordered by idx ascending to feed into the agent.

    Returns a list of dicts, e.g. [{"role": "user", "content": "..."}, ...].
    """
    engine = engine or get_async_engine()
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                """
                SELECT role, content, idx
                FROM messages
                WHERE thread_id = :thread_id
                ORDER BY idx DESC
                LIMIT :limit
                """
            ),
            {"thread_id": str(thread_id), "limit": int(limit)},
        )
        rows = list(res.fetchall())

    rows.sort(key=lambda r: r[2])
    return [_row_to_agent_message(r) for r in rows]


async def load_recent_messages_for_default_thread(
    limit: Optional[int] = None, *, engine: Optional[AsyncEngine] = None
) -> Tuple[uuid.UUID, List[Dict[str, Any]]]:
    """Return (thread_id, recent_messages) for the default thread.

    If limit is None, uses settings.ai_history_limit.
    """
    engine = engine or get_async_engine()
    thread_id = await get_or_create_default_thread(engine=engine)
    limit_val = settings.ai_history_limit if limit is None else limit
    messages = await load_recent_messages_for_thread(thread_id, limit_val, engine=engine)
    return thread_id, messages


async def append_message(
    thread_id: uuid.UUID, role: str, content: Any, *, engine: Optional[AsyncEngine] = None
) -> int:
    """Append a single message to the thread.

    Returns the assigned idx of the new row. The first message uses idx = 0.
    """
    engine = engine or get_async_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                WITH next_idx AS (
                  SELECT COALESCE(MAX(idx), -1) + 1 AS idx
                  FROM messages
                  WHERE thread_id = :thread_id
                )
                INSERT INTO messages (thread_id, idx, role, content)
                SELECT :thread_id, next_idx.idx, :role, :content::jsonb
                FROM next_idx
                RETURNING idx
                """
            ),
            {
                "thread_id": str(thread_id),
                "role": role,
                "content": json.dumps(content),
            },
        )
        row = result.first()
        return int(row[0])


async def append_messages(
    thread_id: uuid.UUID, messages: Iterable[Dict[str, Any]], *, engine: Optional[AsyncEngine] = None
) -> List[int]:
    """Append multiple messages in order, assigning sequential idx values.

    Returns list of assigned idx values in the same order as input.
    """
    engine = engine or get_async_engine()
    assigned: List[int] = []
    async with engine.begin() as conn:
        # Get starting index once within the transaction
        res = await conn.execute(
            text("SELECT COALESCE(MAX(idx), -1) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": str(thread_id)},
        )
        start_idx = int(res.scalar_one())

        for offset, message in enumerate(messages, start=1):
            idx_val = start_idx + offset
            await conn.execute(
                text(
                    """
                    INSERT INTO messages (thread_id, idx, role, content)
                    VALUES (:thread_id, :idx, :role, :content::jsonb)
                    """
                ),
                {
                    "thread_id": str(thread_id),
                    "idx": idx_val,
                    "role": str(message.get("role")),
                    "content": json.dumps(message.get("content")),
                },
            )
            assigned.append(idx_val)
    return assigned


# ---------- Utilities ----------

async def count_messages(thread_id: uuid.UUID, *, engine: Optional[AsyncEngine] = None) -> int:
    engine = engine or get_async_engine()
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": str(thread_id)},
        )
        return int(res.scalar_one())


async def get_last_index(thread_id: uuid.UUID, *, engine: Optional[AsyncEngine] = None) -> Optional[int]:
    engine = engine or get_async_engine()
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT MAX(idx) FROM messages WHERE thread_id = :thread_id"),
            {"thread_id": str(thread_id)},
        )
        value = res.scalar_one()
        return None if value is None else int(value)


async def export_thread(thread_id: uuid.UUID, *, engine: Optional[AsyncEngine] = None) -> Dict[str, Any]:
    """Return thread metadata and all messages ordered by idx for inspection."""
    engine = engine or get_async_engine()
    async with engine.connect() as conn:
        thr = await conn.execute(
            text("SELECT id, title, created_at FROM threads WHERE id = :id"),
            {"id": str(thread_id)},
        )
        thread_row = thr.first()

        msgs = await conn.execute(
            text(
                """
                SELECT idx, role, content, created_at
                FROM messages
                WHERE thread_id = :thread_id
                ORDER BY idx ASC
                """
            ),
            {"thread_id": str(thread_id)},
        )
        messages = [
            {
                "idx": int(r[0]),
                "role": r[1],
                "content": r[2],
                "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else r[3],
            }
            for r in msgs.fetchall()
        ]

    return {
        "thread": {
            "id": str(thread_row[0]) if thread_row else str(thread_id),
            "title": thread_row[1] if thread_row else None,
            "created_at": thread_row[2].isoformat() if thread_row and hasattr(thread_row[2], "isoformat") else None,
        },
        "messages": messages,
    }


# ---------- Integration helpers ----------

async def prepare_default_thread_history(limit: Optional[int] = None) -> Tuple[uuid.UUID, List[Dict[str, Any]]]:
    """Ensure schema exists, ensure default thread exists, and load recent history.

    Intended usage before each agent call:
    - Call this to get (thread_id, message_history) to pass into the Agent.
    - After the Agent completes, persist newly produced messages with append_messages.
    """
    await init_schema()
    return await load_recent_messages_for_default_thread(limit=limit)


