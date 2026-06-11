"""DataOps: verifica frescor e qualidade das fontes de dados (PNCP, BLL, etc.)."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

QUALITY_GATES: dict[str, dict[str, Any]] = {
    "pncp": {
        "freshness_max_hours": 4,
        "min_editais_por_dia": 100,
        "campos_obrigatorios_pct": 0.95,
        "probe_url": "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
                     "?dataInicial=2024-01-01&dataFinal=2024-01-01&pagina=1&tamanhoPagina=1",
    },
    "bll": {
        "freshness_max_hours": 8,
        "min_editais_por_dia": 20,
        "campos_obrigatorios_pct": 0.90,
        "probe_url": "https://bll.org.br/api/v1/licitacoes?limit=1",
    },
}


@dataclass
class DataSourceHealth:
    source_name: str
    checked_at: float = field(default_factory=time.time)
    editais_count: int | None = None
    campos_obrigatorios_pct: float | None = None
    pdf_legibilidade_pct: float | None = None
    is_fresh: bool = True
    latency_ms: int | None = None
    error: str | None = None
    hours_since_update: float | None = None


async def check_source(source: str) -> DataSourceHealth:
    gates = QUALITY_GATES.get(source)
    if not gates:
        return DataSourceHealth(source_name=source, error="Fonte desconhecida")

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(gates["probe_url"])
            latency_ms = int((time.time() - t0) * 1000)
            resp.raise_for_status()
            data = resp.json()
            count = (
                data.get("totalRegistros")
                or data.get("total")
                or (len(data) if isinstance(data, list) else None)
            )
            return DataSourceHealth(
                source_name=source,
                latency_ms=latency_ms,
                editais_count=int(count) if count is not None else None,
                is_fresh=True,
            )
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.warning("data_quality_checker: %s probe falhou: %s", source, exc)
        return DataSourceHealth(
            source_name=source,
            latency_ms=latency_ms,
            is_fresh=False,
            error=str(exc),
        )


async def check_all_sources() -> list[DataSourceHealth]:
    import asyncio
    results = await asyncio.gather(*[check_source(s) for s in QUALITY_GATES])
    return list(results)
