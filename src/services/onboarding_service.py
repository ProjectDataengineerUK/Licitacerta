"""Coach Onboarding service — track dica progress per tenant."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from src.schemas.onboarding import CoachDica, DicaCategoria, OnboardingProgress

logger = logging.getLogger(__name__)


def _row_to_dica(row: dict[str, Any]) -> CoachDica:
    return CoachDica(
        id=row["id"],
        titulo=row["titulo"],
        descricao=row["descricao"],
        categoria=DicaCategoria(row["categoria"]),
        rota_sugerida=row.get("rota_sugerida"),
        ordem=row["ordem"],
    )


async def get_progress(tenant_id: str, conn: Any) -> OnboardingProgress:
    try:
        dicas_rows = await conn.fetch(
            "SELECT id, titulo, descricao, categoria, rota_sugerida, ordem FROM coach_dicas WHERE ativo=TRUE ORDER BY ordem"
        )
        progresso_rows = await conn.fetch(
            "SELECT dica_id, visto_em, dispensado_em FROM onboarding_progresso WHERE tenant_id=$1",
            uuid.UUID(tenant_id) if tenant_id else uuid.uuid4(),
        )
    except Exception as exc:
        logger.warning("onboarding: db error fetching progress: %s", exc)
        return OnboardingProgress(tenant_id=tenant_id)

    total = len(dicas_rows)
    if total == 0:
        return OnboardingProgress(tenant_id=tenant_id)

    vistas = [str(r["dica_id"]) for r in progresso_rows if r["visto_em"] is not None]
    dispensadas = [str(r["dica_id"]) for r in progresso_rows if r["dispensado_em"] is not None]
    feitas = set(vistas) | set(dispensadas)

    pct = round(len(feitas) / total * 100, 1)

    proxima: CoachDica | None = None
    for row in dicas_rows:
        if row["id"] not in feitas:
            proxima = _row_to_dica(dict(row))
            break

    return OnboardingProgress(
        tenant_id=tenant_id,
        dicas_vistas=vistas,
        dicas_dispensadas=dispensadas,
        pct_concluido=pct,
        proxima_dica=proxima,
    )


async def marcar_vista(
    tenant_id: str,
    dica_id: str,
    dispensar: bool,
    conn: Any,
) -> None:
    tid = uuid.UUID(tenant_id) if tenant_id else uuid.uuid4()
    if dispensar:
        await conn.execute(
            """INSERT INTO onboarding_progresso (tenant_id, dica_id, dispensado_em)
               VALUES ($1,$2,NOW())
               ON CONFLICT (tenant_id, dica_id) DO UPDATE SET dispensado_em=NOW()""",
            tid, dica_id,
        )
    else:
        await conn.execute(
            """INSERT INTO onboarding_progresso (tenant_id, dica_id, visto_em)
               VALUES ($1,$2,NOW())
               ON CONFLICT (tenant_id, dica_id) DO UPDATE SET visto_em=NOW()""",
            tid, dica_id,
        )
