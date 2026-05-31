"""MULTI_PORTAL — adapter pattern, dedup, isolamento de falha, health."""
from __future__ import annotations

from datetime import datetime

import pytest

from src.portals.base import (
    PortalAdapter,
    PortalFilter,
    PortalHealthStatus,
    RawEdital,
    normalize_objeto,
)
from src.portals.orchestrator import PortalOrchestrator
from src.portals.pncp import PNCPAdapter


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeAdapter(PortalAdapter):
    def __init__(self, portal_id: str, editais: list[RawEdital] | None = None, boom: Exception | None = None):
        self.portal_id = portal_id
        self.portal_name = portal_id.upper()
        self._editais = editais or []
        self._boom = boom

    async def fetch_new_editals(self, since, filters=None):
        if self._boom is not None:
            raise self._boom
        return self._editais


class _FakePNCPClient:
    def __init__(self, rows):
        self._rows = rows

    async def search_publicacoes_all(self, data_inicial, data_final):
        return self._rows


def _edital(portal_id, ref, *, cnpj="12345678000195", objeto="Obra X", valor=1000.0, sessao=None):
    return RawEdital(
        portal_id=portal_id,
        portal_edital_ref=ref,
        orgao_cnpj=cnpj,
        objeto=objeto,
        valor_estimado_brl=valor,
        data_sessao=sessao or datetime(2026, 6, 1, 10, 0),
    )


# --------------------------------------------------------------------------- #
# dedup_hash
# --------------------------------------------------------------------------- #
def test_normalize_objeto_collapses_whitespace_and_case():
    assert normalize_objeto("  Obra   DE  Limpeza ") == "obra de limpeza"


def test_dedup_hash_stable_across_portals():
    a = _edital("pncp", "P-1")
    b = _edital("bll", "B-9")  # mesmo cnpj/objeto/valor/data → mesmo hash
    assert a.dedup_hash == b.dedup_hash


def test_dedup_hash_differs_on_objeto():
    a = _edital("pncp", "P-1", objeto="Obra X")
    b = _edital("pncp", "P-2", objeto="Obra Y")
    assert a.dedup_hash != b.dedup_hash


# --------------------------------------------------------------------------- #
# AT-002 — deduplicação entre portais
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_at002_dedup_across_portals():
    pncp = _FakeAdapter("pncp", [_edital("pncp", "P-1")])
    bll = _FakeAdapter("bll", [_edital("bll", "B-9")])  # mesmo edital lógico
    orch = PortalOrchestrator([pncp, bll])

    result = await orch.run(datetime(2026, 5, 1))
    assert len(result.editais) == 1
    assert len(result.duplicados) == 1


# --------------------------------------------------------------------------- #
# AT-003 — isolamento de falha
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_at003_failure_isolation():
    ok = _FakeAdapter("pncp", [_edital("pncp", "P-1")])
    broken = _FakeAdapter("bnc", boom=TimeoutError("timeout"))
    orch = PortalOrchestrator([ok, broken])

    result = await orch.run(datetime(2026, 5, 1))
    assert len(result.editais) == 1  # PNCP processado normalmente
    health = {h.portal_id: h for h in result.health}
    assert health["pncp"].status == "online"
    assert health["bnc"].status == "error"
    assert "TimeoutError" in (health["bnc"].last_error or "")


# --------------------------------------------------------------------------- #
# AT-006 — health check offline
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_at006_health_check_offline():
    broken = _FakeAdapter("bll", boom=ConnectionError("down"))
    status = await broken.health_check()
    assert isinstance(status, PortalHealthStatus)
    assert status.status == "offline"
    assert "ConnectionError" in (status.last_error or "")


# --------------------------------------------------------------------------- #
# AT-001 / AT-005 — PNCPAdapter mapeia e normaliza
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_pncp_adapter_maps_and_normalizes():
    rows = [
        {
            "numeroControlePNCP": "PNCP-0001",
            "objetoCompra": "Aquisição de papel A4",
            "orgaoEntidade": {"cnpj": "00000000000191"},
            "valorTotalEstimado": "5000.50",
            "modalidadeNome": "Pregão Eletrônico",
            "dataAberturaProposta": "2026-06-10T09:00:00",
        }
    ]
    adapter = PNCPAdapter(client=_FakePNCPClient(rows))
    editais = await adapter.fetch_new_editals(datetime(2026, 5, 1), PortalFilter())

    assert len(editais) == 1
    e = editais[0]
    assert e.portal_id == "pncp"
    assert e.portal_edital_ref == "PNCP-0001"
    assert e.orgao_cnpj == "00000000000191"
    assert e.valor_estimado_brl == 5000.50
    assert e.modalidade == "Pregão Eletrônico"
    assert e.data_sessao == datetime(2026, 6, 10, 9, 0)


@pytest.mark.asyncio
async def test_pncp_adapter_tolerates_missing_fields():
    adapter = PNCPAdapter(client=_FakePNCPClient([{"numeroControlePNCP": "X"}]))
    editais = await adapter.fetch_new_editals(datetime(2026, 5, 1))
    assert editais[0].valor_estimado_brl is None
    assert editais[0].orgao_cnpj is None
