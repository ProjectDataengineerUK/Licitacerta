from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.pca_classifier import PCAClassification, PCAClassifierAgent


def _cls(cnae="6209-1", cat="servico", conf=0.9):
    return PCAClassification(segmento_cnae=cnae, categoria=cat, confianca=conf)


@pytest.fixture()
def agent():
    with patch("src.agents.pca_classifier.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        a = PCAClassifierAgent()
    return a, mock_llm


@pytest.mark.asyncio
async def test_classify_ti(agent):
    a, mock_llm = agent
    mock_llm.ainvoke = AsyncMock(return_value=_cls("6209-1", "servico", 0.9))
    r = await a.classify("suporte técnico de TI")
    assert r.segmento_cnae == "6209-1"
    assert r.categoria == "servico"


@pytest.mark.asyncio
async def test_classify_limpeza(agent):
    a, mock_llm = agent
    mock_llm.ainvoke = AsyncMock(return_value=_cls("8121-4", "servico", 0.95))
    r = await a.classify("limpeza predial")
    assert r.segmento_cnae == "8121-4"


@pytest.mark.asyncio
async def test_classify_obra(agent):
    a, mock_llm = agent
    mock_llm.ainvoke = AsyncMock(return_value=_cls("4120-4", "obra", 0.85))
    r = await a.classify("construção de muro")
    assert r.categoria == "obra"


@pytest.mark.asyncio
async def test_classify_error_returns_default(agent):
    a, mock_llm = agent
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("llm error"))
    r = await a.classify("qualquer coisa")
    assert r.segmento_cnae == "0000-0"
    assert r.confianca == 0.0


@pytest.mark.asyncio
async def test_classify_batch_empty(agent):
    a, _ = agent
    r = await a.classify_batch([])
    assert r == []


@pytest.mark.asyncio
async def test_classify_batch_multiple(agent):
    a, mock_llm = agent
    mock_llm.ainvoke = AsyncMock(side_effect=[
        _cls("6209-1", "servico", 0.9),
        _cls("8121-4", "servico", 0.95),
    ])
    r = await a.classify_batch(["suporte TI", "limpeza"])
    assert len(r) == 2
    assert r[0].segmento_cnae == "6209-1"
    assert r[1].segmento_cnae == "8121-4"
