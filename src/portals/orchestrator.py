from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from src.portals.base import PortalAdapter, PortalFilter, PortalHealthStatus, RawEdital

logger = logging.getLogger(__name__)


@dataclass
class PortalRunResult:
    """Resultado consolidado de uma rodada multi-portal."""

    editais: list[RawEdital] = field(default_factory=list)  # únicos (pós-dedup)
    duplicados: list[RawEdital] = field(default_factory=list)
    health: list[PortalHealthStatus] = field(default_factory=list)


class PortalOrchestrator:
    """Coordena múltiplos PortalAdapters em paralelo.

    - Falha de um portal é isolada (não derruba os demais).
    - Deduplica editais por ``dedup_hash`` (primeira ocorrência vence).
    """

    def __init__(self, adapters: list[PortalAdapter]) -> None:
        self._adapters = adapters

    async def run(
        self, since: datetime, filters: PortalFilter | None = None
    ) -> PortalRunResult:
        results = await asyncio.gather(
            *(self._fetch_one(a, since, filters) for a in self._adapters),
        )

        out = PortalRunResult()
        seen: set[str] = set()
        for adapter, editais, health in results:
            out.health.append(health)
            for edital in editais:
                h = edital.dedup_hash
                if h in seen:
                    out.duplicados.append(edital)
                    continue
                seen.add(h)
                out.editais.append(edital)
        return out

    async def _fetch_one(
        self, adapter: PortalAdapter, since: datetime, filters: PortalFilter | None
    ) -> tuple[PortalAdapter, list[RawEdital], PortalHealthStatus]:
        try:
            editais = await adapter.fetch_new_editals(since, filters)
            health = PortalHealthStatus(
                portal_id=adapter.portal_id, status="online", last_run=datetime.now()
            )
            return adapter, editais, health
        except Exception as exc:  # noqa: BLE001 — isolamento de falha por portal
            logger.warning("portal %s falhou: %s", adapter.portal_id, exc)
            health = PortalHealthStatus(
                portal_id=adapter.portal_id,
                status="error",
                last_error=f"{type(exc).__name__}: {exc}",
            )
            return adapter, [], health
