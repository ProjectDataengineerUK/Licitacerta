"""VERTICALIZACAO — contexto, checklist e score de compatibilidade (determinístico)."""
from __future__ import annotations

from src.agents.vertical_context import (
    detect_vertical,
    get_vertical_context,
    habilitacao_checklist,
    system_prompt_suffix,
    vertical_match,
)

_EDITAL_TI = "Contratação de licença de software e suporte técnico para sistema ERP em cloud."
_EDITAL_LIMPEZA = "Prestação de serviços de limpeza, conservação e asseio predial com portaria."
_EDITAL_OBRAS = "Execução de obra de construção e reforma com responsável técnico CREA e planilha SINAPI."


# --------------------------------------------------------------------------- #
# Contexto + prompt
# --------------------------------------------------------------------------- #
def test_get_vertical_context_known_and_unknown():
    assert "compliance_extra" in get_vertical_context("TI_SOFTWARE")
    assert get_vertical_context("OUTRO") == {}
    assert get_vertical_context(None) == {}


def test_system_prompt_suffix_includes_setor():
    suffix = system_prompt_suffix("OBRAS_ENGENHARIA")
    assert "SINAPI" in suffix
    assert system_prompt_suffix(None) == ""


# --------------------------------------------------------------------------- #
# AT-003 — checklist de habilitação por vertical
# --------------------------------------------------------------------------- #
def test_at003_checklist_obras_inclui_crea():
    checklist = habilitacao_checklist("OBRAS_ENGENHARIA")
    assert "registro_crea_responsavel_tecnico" in checklist


def test_checklist_ti_nao_tem_crea():
    checklist = habilitacao_checklist("TI_SOFTWARE")
    assert "registro_crea_responsavel_tecnico" not in checklist
    assert "atestado_capacidade_tecnica_ti" in checklist


def test_checklist_base_sempre_presente():
    for v in (None, "OUTRO", "TI_SOFTWARE", "LIMPEZA_CONSERVACAO"):
        assert "regularidade_fiscal_trabalhista" in habilitacao_checklist(v)


# --------------------------------------------------------------------------- #
# detecção
# --------------------------------------------------------------------------- #
def test_detect_vertical_por_keywords():
    assert detect_vertical(_EDITAL_TI)[0] == "TI_SOFTWARE"
    assert detect_vertical(_EDITAL_LIMPEZA)[0] == "LIMPEZA_CONSERVACAO"
    assert detect_vertical(_EDITAL_OBRAS)[0] == "OBRAS_ENGENHARIA"


def test_detect_vertical_sem_match():
    detected, score = detect_vertical("texto genérico sem termos do setor")
    assert detected is None
    assert score == 0.0


# --------------------------------------------------------------------------- #
# AT-004 — alerta fora do setor
# --------------------------------------------------------------------------- #
def test_at004_alerta_fora_do_setor():
    match = vertical_match(_EDITAL_LIMPEZA, tenant_vertical="TI_SOFTWARE")
    assert match.alerta_fora_do_setor is True
    assert match.vertical_detectada == "LIMPEZA_CONSERVACAO"
    assert match.score_compatibilidade < 0.3


def test_match_dentro_do_setor():
    match = vertical_match(_EDITAL_TI, tenant_vertical="TI_SOFTWARE")
    assert match.alerta_fora_do_setor is False
    assert match.score_compatibilidade > 0.5


def test_match_tenant_outro_nao_alerta():
    match = vertical_match(_EDITAL_OBRAS, tenant_vertical="OUTRO")
    assert match.alerta_fora_do_setor is False
    assert match.vertical_detectada == "OBRAS_ENGENHARIA"
