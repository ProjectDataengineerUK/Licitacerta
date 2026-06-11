"""Tests for PregoeicoService — AT-001..AT-006."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.pregoeiro import PregoeiroPerfil
from src.services.pregoeiro_service import (
    PregoeicoService,
    _build_alertas,
    _calc_indice,
    _normalize,
)


def _make_row(**kwargs):
    defaults = {
        "nome": "João Silva",
        "orgao_nome": "Prefeitura de SP",
        "total_sessoes": 20,
        "taxa_aceitacao_impugnacao_pct": 60.0,
        "taxa_desclassificacao_pct": 10.0,
        "tempo_medio_sessao_horas": 3.0,
        "previsibilidade": 0.8,
        "clausulas_frequentes": "[]",
        "tipos_desclassificacao": "[]",
        "empresas_frequentes_vencedoras": "[]",
    }
    defaults.update(kwargs)
    row = MagicMock()
    row.__getitem__ = lambda self, k: defaults[k]
    row.get = lambda k, default=None: defaults.get(k, default)
    return row


# AT-001: lookup retorna perfil quando pregoeiro existe no banco
@pytest.mark.asyncio
async def test_lookup_found():
    db = AsyncMock()
    db.fetchrow.return_value = _make_row()
    svc = PregoeicoService(db)
    perfil = await svc.lookup("João Silva", "12345678000190")
    assert perfil.nome == "João Silva"
    assert perfil.total_sessoes == 20
    assert perfil.indice_reputacao is not None
    assert perfil.label_confianca != "Sem dados"


# AT-002: lookup retorna PregoeiroPerfil vazio quando pregoeiro não existe
@pytest.mark.asyncio
async def test_lookup_not_found():
    db = AsyncMock()
    db.fetchrow.return_value = None
    svc = PregoeicoService(db)
    perfil = await svc.lookup("Fulano Desconhecido", "00000000000000")
    assert perfil.total_sessoes == 0
    assert perfil.indice_reputacao is None
    assert perfil.label_confianca == "Sem dados"


# AT-003: erro de DB retorna perfil default graciosamente
@pytest.mark.asyncio
async def test_lookup_db_error_graceful():
    db = AsyncMock()
    db.fetchrow.side_effect = Exception("connection refused")
    svc = PregoeicoService(db)
    perfil = await svc.lookup("Qualquer Nome", "99999999000100")
    assert isinstance(perfil, PregoeiroPerfil)
    assert perfil.total_sessoes == 0


# AT-004: _calc_indice é calculado corretamente
def test_calc_indice_formula():
    # base 50 + (60-50)*0.3 - 0 + 0.8*20 - 0 = 50 + 3 + 16 = 69
    score = _calc_indice(
        taxa_aceitacao=60.0,
        taxa_desclassificacao=10.0,
        previsibilidade=0.8,
        tempo_medio=3.0,
    )
    assert abs(score - 69.0) < 0.01


def test_calc_indice_clamps_to_100():
    score = _calc_indice(taxa_aceitacao=200.0, taxa_desclassificacao=0.0, previsibilidade=1.0, tempo_medio=0.0)
    assert score == 100.0


def test_calc_indice_clamps_to_zero():
    score = _calc_indice(taxa_aceitacao=0.0, taxa_desclassificacao=100.0, previsibilidade=0.0, tempo_medio=20.0)
    assert score == 0.0


# AT-005: alertas gerados corretamente
def test_alertas_alta_impugnacao():
    alertas = _build_alertas(taxa_impugnacao=85.0, taxa_desclassificacao=10.0, tempo_medio=3.0)
    assert any("impugnação" in a.lower() or "impugnaç" in a.lower() for a in alertas)


def test_alertas_alta_desclassificacao():
    alertas = _build_alertas(taxa_impugnacao=30.0, taxa_desclassificacao=30.0, tempo_medio=3.0)
    assert any("desclassificação" in a.lower() or "desclassificaç" in a.lower() for a in alertas)


def test_alertas_sessao_longa():
    alertas = _build_alertas(taxa_impugnacao=30.0, taxa_desclassificacao=10.0, tempo_medio=10.0)
    assert any("sessão" in a.lower() or "sessõ" in a.lower() or "longa" in a.lower() for a in alertas)


# AT-006: confiança é baseada no número de sessões
@pytest.mark.asyncio
async def test_confianca_sem_dados_suficientes():
    db = AsyncMock()
    db.fetchrow.return_value = _make_row(total_sessoes=3)
    svc = PregoeicoService(db)
    perfil = await svc.lookup("Novo Pregoeiro", "12345678000190")
    assert perfil.confianca_pct < 1.0
    assert "formação" in perfil.label_confianca.lower()


@pytest.mark.asyncio
async def test_confianca_dados_suficientes():
    db = AsyncMock()
    db.fetchrow.return_value = _make_row(total_sessoes=15)
    svc = PregoeicoService(db)
    perfil = await svc.lookup("Experiente", "12345678000190")
    assert perfil.confianca_pct >= 1.0
    assert "sessões" in perfil.label_confianca.lower()


# Normalização — sem diacríticos
def test_normalize_strips_accents():
    assert _normalize("João") == "joao"
    assert _normalize("Prätorium") == "pratorium"
