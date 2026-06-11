from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def hash_ip(ip: str | None) -> str:
    return hashlib.sha256((ip or "").encode("utf-8")).hexdigest()


async def log_consent(
    *,
    user_id: str,
    version: str,
    ip: str | None,
    accepted_tou: bool,
    accepted_privacy: bool,
    conn: Any,
) -> None:
    # APPEND-ONLY: sempre INSERT, nunca UPDATE/DELETE em consent_log
    ip_hash = hash_ip(ip)
    await conn.execute(
        """INSERT INTO consent_log
            (user_id, version, ip_hash, accepted_tou, accepted_privacy, accepted_at)
           VALUES ($1, $2, $3, $4, $5, NOW())""",
        user_id,
        version,
        ip_hash,
        accepted_tou,
        accepted_privacy,
    )


async def has_valid_consent(*, user_id: str, version: str, conn: Any) -> bool:
    row = await conn.fetchrow(
        """SELECT accepted_tou, accepted_privacy FROM consent_log
           WHERE user_id = $1 AND version = $2
           ORDER BY accepted_at DESC LIMIT 1""",
        user_id,
        version,
    )
    if row is None:
        return False
    return bool(row["accepted_tou"]) and bool(row["accepted_privacy"])


async def request_deletion(*, tenant_id: str, user_id: str, conn: Any) -> dict[str, Any]:
    row = await conn.fetchrow(
        """INSERT INTO data_deletion_requests (tenant_id, user_id)
           VALUES ($1, $2)
           ON CONFLICT (user_id) WHERE status IN ('pending', 'processing')
           DO NOTHING
           RETURNING id, requested_at, scheduled_delete_at, status""",
        tenant_id,
        user_id,
    )
    if row is None:
        row = await conn.fetchrow(
            """SELECT id, requested_at, scheduled_delete_at, status
               FROM data_deletion_requests
               WHERE user_id = $1 AND status IN ('pending', 'processing')
               ORDER BY requested_at DESC LIMIT 1""",
            user_id,
        )
    return {
        "id": str(row["id"]),
        "tenant_id": tenant_id,
        "requested_at": row["requested_at"],
        "scheduled_delete_at": row["scheduled_delete_at"],
        "status": row["status"],
    }
