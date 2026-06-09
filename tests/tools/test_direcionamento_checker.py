"""Testes unitários para direcionamento_checker (AT-001..AT-007)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.direcionamento_checker import (
    _check_sinais_tender,
    _validate_language,
    check,
)


class _MockTender:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return None


# ── AT-001: especificacao_unica → sinal detectado com peso 0.20 ──────────────
def test_especificacao_unica_detectada():
    tender = _MockTender(especificacao_tem_marca=True)
    sinais = _check_sinais_tender(tender)
    codigos = {s.codigo for s in sinais}
    assert "especificacao_unica" in codigos
    sinal = next(s for s in sinais if s.codigo == "especificacao_unica")
    assert sinal.peso == 0.20


# ── AT-002: 4 sinais → score = soma pesos × 100 ≤ 100 ────────────────────────
def test_4_sinais_score_correto():
    tender = _MockTender(
        especificacao_tem_marca=True,      # 0.20
        certidao_nao_padrao=True,          # 0.15
        prazo_proposta_dias=2,             # 0.15
        restringe_me_epp=True,             # 0.05
        justificativa_restricao=None,
    )
    sinais = _check_sinais_tender(tender)
    score = min(100.0, sum(s.peso for s in sinais) * 100)
    assert score == pytest.approx(55.0, abs=0.01)
    assert score <= 100.0


# ── AT-003: score≥60 → impugnacao_recomendada=True, nivel=alto ───────────────
def test_alto_impugnacao_recomendada():
    async def _run():
        tender = _MockTender(
            especificacao_tem_marca=True,   # 0.20
            certidao_nao_padrao=True,       # 0.15
            prazo_proposta_dias=2,          # 0.15
            atestado_cnae_restritivo=True,  # 0.15
            valor_referencia_coincide_historico=True,  # 0.10
        )
        # Score = (0.20+0.15+0.15+0.15+0.10)*100 = 75 → alto
        with patch("src.tools.direcionamento_checker._gerar_fundamentacao", new_callable=AsyncMock) as mock_fund:
            mock_fund.return_value = ("Indícios de potencial direcionamento.", ["Acórdão 2.500/2015"])
            return await check(tender)

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.nivel == "alto"
    assert result.impugnacao_recomendada is True
    assert result.score >= 60


# ── AT-004: score<40 → fundamentacao=None, sem chamada LLM ───────────────────
def test_score_baixo_sem_fundamentacao():
    async def _run():
        tender = _MockTender(restricao_porte=True, justificativa_restricao=None)
        # 0.05 × 100 = 5 → baixo
        with patch("src.tools.direcionamento_checker._gerar_fundamentacao", new_callable=AsyncMock) as mock_fund:
            result = await check(tender)
            assert not mock_fund.called
            return result

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result.fundamentacao_impugnacao is None
    assert result.nivel == "baixo"


# ── AT-007: linguagem proibida → ValueError ───────────────────────────────────
def test_validate_language_proibida():
    with pytest.raises(ValueError, match="Linguagem proibida"):
        _validate_language("O edital foi claramente direcionado para empresa X")


def test_validate_language_ok():
    text = "Identificamos sinais de potencial direcionamento no edital."
    assert _validate_language(text) == text


# ── Graceful: tender sem campos → sem sinais ─────────────────────────────────
def test_tender_sem_campos_sem_sinais():
    tender = _MockTender()
    sinais = _check_sinais_tender(tender)
    assert sinais == []
