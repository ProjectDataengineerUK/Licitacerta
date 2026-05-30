from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.radar_predictor import RadarPredictor, _cosine


def _pred(session=None):
    s = session or MagicMock()
    s.execute = AsyncMock()
    return RadarPredictor(s)


def test_data_prevista_historico_mes():
    p = _pred()
    d, f = p.calc_data_prevista(None, historico_mes=3)
    assert f == "sazonalidade"
    assert d.month == 3


def test_data_prevista_historico_passado_avanca_ano():
    p = _pred()
    today = date.today()
    mes = (today - timedelta(days=35)).month
    d, _ = p.calc_data_prevista(None, historico_mes=mes)
    assert d > today


def test_data_prevista_pca_q1():
    p = _pred()
    d, f = p.calc_data_prevista(date(2026, 1, 1), None)
    assert f == "pca"
    assert d.month == 1


def test_data_prevista_pca_q3():
    p = _pred()
    d, f = p.calc_data_prevista(date(2026, 7, 1), None)
    assert f == "pca"
    assert d.month == 7


def test_data_prevista_fallback():
    p = _pred()
    today = date.today()
    d, f = p.calc_data_prevista(None, None)
    assert f == "pca"
    assert d >= today + timedelta(days=59)


def test_confianca_combinado_alto():
    p = _pred()
    c = p.calc_confianca(0.85, "combinado", 3, date(2026, 1, 1))
    assert c >= 70


def test_confianca_baixa_sem_historico():
    p = _pred()
    c = p.calc_confianca(0.30, "pca", 0, None)
    assert c < 30


def test_confianca_nao_excede_100():
    p = _pred()
    c = p.calc_confianca(1.0, "combinado", 5, date(2026, 1, 1))
    assert c <= 100.0


def test_confianca_sazonalidade_maior_pca():
    p = _pred()
    c1 = p.calc_confianca(0.70, "pca", 0, date(2026, 1, 1))
    c2 = p.calc_confianca(0.70, "sazonalidade", 3, date(2026, 1, 1))
    assert c2 > c1


def test_cosine_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(_cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_zero():
    assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


@pytest.mark.asyncio
async def test_generate_skips_no_embedder():
    with patch("src.services.radar_predictor._get_embedder", return_value=None):
        p = _pred()
        r = await p.generate_for_tenant(uuid4(), ["TI"])
    assert r == []


@pytest.mark.asyncio
async def test_generate_skips_below_threshold():
    session = MagicMock()
    mock_row = MagicMock(
        id=uuid4(),
        orgao_cnpj="12345678000195",
        orgao_nome="ANATEL",
        descricao="combustível",
        valor_estimado_brl=10000,
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=None,
        segmento_cnae="4731-8",
    )
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    session.execute = AsyncMock(return_value=mock_result)

    embedder = MagicMock()
    embedder.aembed_query = AsyncMock(return_value=[1.0, 0.0, 0.0])
    embedder.aembed_documents = AsyncMock(return_value=[[0.0, 1.0, 0.0]])

    with patch("src.services.radar_predictor._get_embedder", return_value=embedder):
        p = RadarPredictor(session)
        r = await p.generate_for_tenant(uuid4(), ["TI"])
    assert r == []
