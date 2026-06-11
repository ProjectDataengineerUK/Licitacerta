"""Tests for onboarding_service — AT-001..AT-006."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.services.onboarding_service import get_progress, marcar_vista


def _make_dica_rows(n: int = 3):
    return [
        {
            "id": f"d0{i}_dica",
            "titulo": f"Dica {i}",
            "descricao": f"Desc {i}",
            "categoria": "inicio",
            "rota_sugerida": None,
            "ordem": i,
        }
        for i in range(1, n + 1)
    ]


async def _make_conn(dicas=None, progresso=None):
    conn = AsyncMock()
    if dicas is None:
        dicas = _make_dica_rows(3)
    if progresso is None:
        progresso = []
    conn.fetch = AsyncMock(side_effect=[dicas, progresso])
    conn.execute = AsyncMock()
    return conn


# AT-001: no progress → pct=0, proxima_dica = first dica
@pytest.mark.asyncio
async def test_at001_no_progress():
    conn = await _make_conn()
    result = await get_progress("tenant-1", conn)
    assert result.pct_concluido == 0.0
    assert result.proxima_dica is not None
    assert result.proxima_dica.id == "d01_dica"


# AT-002: all dicas seen → pct=100, proxima_dica=None
@pytest.mark.asyncio
async def test_at002_all_seen():
    dicas = _make_dica_rows(2)
    progresso = [
        {"dica_id": "d01_dica", "visto_em": "2026-06-01", "dispensado_em": None},
        {"dica_id": "d02_dica", "visto_em": "2026-06-02", "dispensado_em": None},
    ]
    conn = await _make_conn(dicas, progresso)
    result = await get_progress("tenant-1", conn)
    assert result.pct_concluido == 100.0
    assert result.proxima_dica is None


# AT-003: first dica dispensed → proxima_dica = second
@pytest.mark.asyncio
async def test_at003_first_dispensed_proxima_second():
    dicas = _make_dica_rows(3)
    progresso = [
        {"dica_id": "d01_dica", "visto_em": None, "dispensado_em": "2026-06-01"},
    ]
    conn = await _make_conn(dicas, progresso)
    result = await get_progress("tenant-1", conn)
    assert result.proxima_dica is not None
    assert result.proxima_dica.id == "d02_dica"


# AT-004: DB error → returns empty OnboardingProgress (graceful)
@pytest.mark.asyncio
async def test_at004_db_error_graceful():
    conn = AsyncMock()
    conn.fetch = AsyncMock(side_effect=Exception("connection refused"))
    result = await get_progress("tenant-1", conn)
    assert result.pct_concluido == 0.0
    assert result.proxima_dica is None
    assert result.dicas_vistas == []


# AT-005: marcar_vista → calls INSERT with visto_em
@pytest.mark.asyncio
async def test_at005_marcar_vista_seen():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    await marcar_vista("tenant-1", "d01_dica", dispensar=False, conn=conn)
    conn.execute.assert_called_once()
    call_sql = conn.execute.call_args[0][0]
    assert "visto_em" in call_sql


# AT-006: marcar_vista dispensar=True → calls INSERT with dispensado_em
@pytest.mark.asyncio
async def test_at006_marcar_vista_dispensar():
    conn = AsyncMock()
    conn.execute = AsyncMock()
    await marcar_vista("tenant-1", "d01_dica", dispensar=True, conn=conn)
    call_sql = conn.execute.call_args[0][0]
    assert "dispensado_em" in call_sql
