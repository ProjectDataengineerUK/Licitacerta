"""Prompt version registry backed by AlloyDB.

Agents load the active prompt on startup via `get_active_prompt()`.
Rollback = set active=true on a previous version — no redeployment needed.
"""
from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Fallback prompts used when DB is unavailable (mirrors current hardcoded prompts).
_FALLBACKS: dict[str, str] = {}


def register_fallback(agent_name: str, system_prompt: str) -> None:
    """Called at module load time by each agent to register its hardcoded prompt."""
    _FALLBACKS[agent_name] = system_prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def get_active_prompt(agent_name: str, db_url: str | None = None) -> str:
    """Return the active system prompt for *agent_name* from AlloyDB.

    Falls back to the registered hardcoded prompt when DB is unreachable.
    """
    try:
        import asyncpg
        url = db_url or _get_db_url()
        if not url:
            raise RuntimeError("DATABASE_URL not set")
        conn = await asyncpg.connect(url)
        try:
            row = await conn.fetchrow(
                "SELECT system_prompt FROM prompt_versions "
                "WHERE agent_name = $1 AND active = true LIMIT 1",
                agent_name,
            )
        finally:
            await conn.close()
        if row:
            return row["system_prompt"]
    except Exception as exc:
        logger.warning("prompt_registry: DB unavailable for %s (%s) — using fallback", agent_name, exc)
    return _FALLBACKS.get(agent_name, "")


async def rollback_prompt(agent_name: str, target_version: str, db_url: str | None = None) -> None:
    """Set *target_version* as active; deactivate all others for the agent."""
    import asyncpg
    url = db_url or _get_db_url()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            await conn.execute(
                "UPDATE prompt_versions SET active = false WHERE agent_name = $1",
                agent_name,
            )
            rows = await conn.execute(
                "UPDATE prompt_versions SET active = true, deployed_at = NOW(), rolled_back = false "
                "WHERE agent_name = $1 AND version = $2",
                agent_name,
                target_version,
            )
        if rows == "UPDATE 0":
            raise ValueError(f"Version {target_version} not found for agent {agent_name}")
    finally:
        await conn.close()
    logger.info("prompt_registry: rolled back %s → %s", agent_name, target_version)


async def register_version(
    agent_name: str,
    version: str,
    system_prompt: str,
    author: str | None = None,
    changelog: str | None = None,
    set_active: bool = False,
    db_url: str | None = None,
) -> str:
    """Insert a new prompt version. Returns the SHA256 hash."""
    import asyncpg
    url = db_url or _get_db_url()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    sha = _sha256(system_prompt)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            if set_active:
                await conn.execute(
                    "UPDATE prompt_versions SET active = false WHERE agent_name = $1",
                    agent_name,
                )
            await conn.execute(
                """INSERT INTO prompt_versions
                   (agent_name, version, hash, system_prompt, author, changelog, active, deployed_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, CASE WHEN $7 THEN NOW() ELSE NULL END)
                   ON CONFLICT (agent_name, version) DO UPDATE
                   SET hash=$3, system_prompt=$4, author=$5, changelog=$6""",
                agent_name,
                version,
                sha,
                system_prompt,
                author,
                changelog,
                set_active,
            )
    finally:
        await conn.close()
    return sha


def _get_db_url() -> str | None:
    import os
    return os.environ.get("DATABASE_URL")
