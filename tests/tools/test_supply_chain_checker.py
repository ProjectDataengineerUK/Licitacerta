"""Testes unitários para supply_chain_checker (AT-001..AT-006)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from src.schemas.supply_chain import APICheck
from src.tools.supply_chain_checker import (
    _aggregate_status,
    _detect_categoria,
    check,
)


# ── AT-001: Detecção de categoria via CNAE ────────────────────────────────────
def test_detect_categoria_cnae_material_hospitalar():
    cat = _detect_categoria("3250-7/01", "produto qualquer")
    assert cat == "material_hospitalar"


def test_detect_categoria_cnae_medicamentos():
    cat = _detect_categoria("2121-1/00", "produto qualquer")
    assert cat == "medicamentos"


def test_detect_categoria_cnae_ti_hardware():
    cat = _detect_categoria("2621-3/00", "produto qualquer")
    assert cat == "ti_hardware"


# ── AT-002: Detecção de categoria via keyword (sem CNAE) ─────────────────────
def test_detect_categoria_keyword_hospitalar():
    cat = _detect_categoria(None, "Material cirúrgico descartável")
    assert cat == "material_hospitalar"


def test_detect_categoria_keyword_alimentos():
    cat = _detect_categoria(None, "Bebida láctea UHT")
    assert cat == "alimentos"


def test_detect_categoria_keyword_ti():
    cat = _detect_categoria(None, "Notebook Dell Core i7")
    assert cat == "ti_hardware"


def test_detect_categoria_nenhuma():
    cat = _detect_categoria(None, "Serviço de limpeza predial")
    assert cat is None


# ── AT-003: Agregação de status ───────────────────────────────────────────────
def test_aggregate_reprovado_ganha():
    checks = [
        APICheck(api="anvisa", status="aprovado"),
        APICheck(api="ceis", status="reprovado"),
        APICheck(api="bpf", status="nao_verificado"),
    ]
    assert _aggregate_status(checks) == "reprovado"


def test_aggregate_pendente_sem_reprovado():
    checks = [
        APICheck(api="anvisa", status="pendente_regularizacao"),
        APICheck(api="ceis", status="nao_verificado"),
    ]
    assert _aggregate_status(checks) == "pendente_regularizacao"


def test_aggregate_nao_verificado_sem_reprovado_pendente():
    checks = [
        APICheck(api="anvisa", status="aprovado"),
        APICheck(api="ceis", status="nao_verificado"),
    ]
    assert _aggregate_status(checks) == "nao_verificado"


def test_aggregate_todos_aprovados():
    checks = [
        APICheck(api="anvisa", status="aprovado"),
        APICheck(api="ceis", status="aprovado"),
    ]
    assert _aggregate_status(checks) == "aprovado"


# ── AT-004: check() retorna None para categoria desconhecida ─────────────────
def test_check_retorna_none_sem_categoria():
    result = asyncio.get_event_loop().run_until_complete(
        check(
            produto_descricao="Serviço de pintura predial",
            fabricante_nome="Empresa X",
            fabricante_cnpj="00000000000191",
            segmento_cnae=None,
        )
    )
    assert result is None


# ── AT-005: Falha de API → nao_verificado (nunca bloqueia pipeline) ──────────
def test_check_api_failure_retorna_nao_verificado():

    async def _run():
        with patch("src.tools.supply_chain_checker._check_ceis", new_callable=AsyncMock) as mock_ceis, \
             patch("src.tools.supply_chain_checker._check_anvisa", new_callable=AsyncMock) as mock_anvisa, \
             patch("src.tools.supply_chain_checker._check_bpf", new_callable=AsyncMock) as mock_bpf:
            mock_ceis.side_effect = Exception("Timeout")
            mock_anvisa.side_effect = Exception("Timeout")
            mock_bpf.side_effect = Exception("Timeout")
            return await check(
                produto_descricao="Curativo hospitalar",
                fabricante_nome="Farmacêutica LTDA",
                fabricante_cnpj="12345678000195",
                segmento_cnae="3250",
            )

    result = asyncio.get_event_loop().run_until_complete(_run())
    # Mesmo com exceções nos mocks internos, _call_api captura e retorna nao_verificado
    # Então o status_geral deve ser nao_verificado (não reprovado)
    assert result is not None
    assert result.status_geral in ("nao_verificado", "aprovado")
    assert result.bloqueante is False


# ── AT-006: CEIS reprovado → bloqueante=True ─────────────────────────────────
def test_check_ceis_reprovado_bloqueante():
    async def _run():
        with patch("src.tools.supply_chain_checker._call_api", new_callable=AsyncMock) as mock_call:
            async def _side_effect(api: str, cnpj: str, produto: str) -> APICheck:
                if api == "ceis":
                    return APICheck(api="ceis", status="reprovado", nota="Sanção ativa no CEIS")
                return APICheck(api=api, status="aprovado")

            mock_call.side_effect = _side_effect
            return await check(
                produto_descricao="Curativo hospitalar",
                fabricante_nome="Farmacêutica LTDA",
                fabricante_cnpj="12345678000195",
                segmento_cnae="3250",
            )

    result = asyncio.get_event_loop().run_until_complete(_run())
    assert result is not None
    assert result.status_geral == "reprovado"
    assert result.bloqueante is True
    assert "ceis" in (result.fundamentacao or "")
