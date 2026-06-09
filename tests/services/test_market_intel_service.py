"""Testes unitários para MarketIntelService (AT-003, AT-004, AT-005, AT-007)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.market_intel_service import MarketIntelService


def _mock_db():
    return AsyncMock()


# ── AT-003: organ_score prazo 25 dias, sem inadimplência → score 100 ──────────
@pytest.mark.asyncio
async def test_organ_score_bom_pagador():
    db = _mock_db()
    db.fetchrow.return_value = {
        "amostra": 10,
        "prazo_medio": Decimal("25"),
        "orgao_cnpj": "00000000000100",
        "orgao_nome": "Ministério Teste",
        "uasg": "123456",
        "indice_inadimplencia": Decimal("0"),
    }
    svc = MarketIntelService(db)
    result = await svc.organ_score(uasg="123456")

    assert result.score == 100
    assert result.label == "Bom Pagador"
    assert not result.alerta_inadimplencia
    assert not result.data_insuficiente


# ── AT-004: organ_score prazo 90 dias + inadimplência → score 0, Risco Alto ──
@pytest.mark.asyncio
async def test_organ_score_risco_alto():
    db = _mock_db()
    db.fetchrow.return_value = {
        "amostra": 15,
        "prazo_medio": Decimal("120"),
        "orgao_cnpj": "99999999000199",
        "orgao_nome": "Órgão Inadimplente",
        "uasg": "999999",
        "indice_inadimplencia": Decimal("0.5"),  # 50%
    }
    svc = MarketIntelService(db)
    result = await svc.organ_score(uasg="999999")

    # 100 - (120-30)*1.0 - 50*2.0 = 100 - 90 - 100 = -90 → clamp → 0
    assert result.score == 0
    assert result.label == "Risco Alto"
    assert result.alerta_inadimplencia


# ── AT-005: data_insuficiente quando amostra < 3 ──────────────────────────────
@pytest.mark.asyncio
async def test_organ_score_insuficiente():
    db = _mock_db()
    db.fetchrow.return_value = {
        "amostra": 1,
        "prazo_medio": None,
        "orgao_cnpj": "00000000000199",
        "orgao_nome": None,
        "uasg": None,
        "indice_inadimplencia": None,
    }
    svc = MarketIntelService(db)
    result = await svc.organ_score(orgao_cnpj="00000000000199")

    assert result.data_insuficiente
    assert result.score == 50
    assert result.label == "Regular"


# ── AT-007: segment_summary concentração alta ─────────────────────────────────
@pytest.mark.asyncio
async def test_segment_summary_concentrado():
    db = _mock_db()
    db.fetch.return_value = [
        {
            "fornecedor_cnpj": "11111111000100",
            "nome": "Empresa Dominante LTDA",
            "total": 50,
            "share": Decimal("0.60"),
        },
        {
            "fornecedor_cnpj": "22222222000100",
            "nome": "Segunda Empresa ME",
            "total": 20,
            "share": Decimal("0.24"),
        },
    ]
    svc = MarketIntelService(db)
    result = await svc.segment_summary("6201-5")

    assert result["concentracao_alta"] is True
    assert result["cnpj_dominante"] == "11111111000100"
    assert len(result["top_fornecedores"]) == 2
    assert result["top_fornecedores"][0]["share_pct"] == 60.0


@pytest.mark.asyncio
async def test_segment_summary_nao_concentrado():
    db = _mock_db()
    db.fetch.return_value = [
        {"fornecedor_cnpj": "11111111000100", "nome": "A", "total": 10, "share": Decimal("0.20")},
        {"fornecedor_cnpj": "22222222000100", "nome": "B", "total": 9, "share": Decimal("0.18")},
    ]
    svc = MarketIntelService(db)
    result = await svc.segment_summary("6201-5")

    assert result["concentracao_alta"] is False
    assert result["cnpj_dominante"] is None


# ── price_benchmark data_insuficiente (amostra < 3) ───────────────────────────
@pytest.mark.asyncio
async def test_price_benchmark_insuficiente():
    db = _mock_db()
    db.fetchrow.return_value = {
        "amostra": 2,
        "media": None,
        "minimo": None,
        "maximo": None,
        "p25": None,
        "p75": None,
    }
    svc = MarketIntelService(db)
    result = await svc.price_benchmark("notebook 15 polegadas", catmat_code="4925")

    assert result.data_insuficiente
    assert result.amostra == 2
