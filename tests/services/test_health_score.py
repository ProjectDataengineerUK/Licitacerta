"""SCORE_SAUDE_OPERACAO — testes unitários para calcular_score().

Função pura: sem I/O, sem mocks necessários.
asyncio_mode=auto no pyproject — nenhum decorator @pytest.mark.asyncio.
"""
from __future__ import annotations

import pytest

from src.schemas.health import ScoreInputs
from src.services.health_score import calcular_score

# ---------------------------------------------------------------------------
# Fixtures de inputs reutilizáveis
# ---------------------------------------------------------------------------

def _inputs_saudaveis(**overrides) -> ScoreInputs:
    """Baseline de tenant saudável: 8/10 vitórias, análise recente, tudo zerado."""
    base = dict(
        runs_ganhos_90d=8,
        runs_total_90d=10,
        tem_analise_recente_30d=True,
        contratos_criticos=0,
        certidoes_vencendo_15d=0,
        certidoes_vencidas=0,
        empenhos_atrasados=0,
        concentracao_orgao=0.2,
        previous_score=None,
    )
    base.update(overrides)
    return ScoreInputs(**base)


def _componente(score, nome: str):
    """Retorna o ComponenteScore pelo nome."""
    return next(c for c in score.componentes if c.nome == nome)


# ---------------------------------------------------------------------------
# AT-001: operação saudável → score >= 80 e label "Excelente" ou "Bom"
# ---------------------------------------------------------------------------

def test_at001_operacao_saudavel_score_e_label():
    inp = _inputs_saudaveis()
    result = calcular_score(inp)

    assert result.score >= 80, f"score esperado >= 80, obtido {result.score}"
    assert result.label in ("Excelente", "Bom"), (
        f"label esperado 'Excelente' ou 'Bom', obtido '{result.label}'"
    )


# ---------------------------------------------------------------------------
# AT-002: 1 certidão vencida → componente certidoes_validas == 70.0
# ---------------------------------------------------------------------------

def test_at002_certidao_vencida_componente_certidoes():
    # 100 - 1*30 = 70
    inp = _inputs_saudaveis(certidoes_vencidas=1)
    result = calcular_score(inp)

    comp = _componente(result, "certidoes_validas")
    assert comp.valor == 70.0, (
        f"componente certidoes_validas: esperado 70.0, obtido {comp.valor}"
    )


# ---------------------------------------------------------------------------
# AT-003: sem análise recente → pipeline_ativo == 20 e recomendação de pipeline
# ---------------------------------------------------------------------------

def test_at003_sem_analise_pipeline_ativo_e_recomendacao():
    inp = _inputs_saudaveis(tem_analise_recente_30d=False)
    result = calcular_score(inp)

    comp = _componente(result, "pipeline_ativo")
    assert comp.valor == 20.0, (
        f"componente pipeline_ativo: esperado 20.0, obtido {comp.valor}"
    )

    titulos = [r.titulo for r in result.recomendacoes]
    assert any("pipeline" in t.lower() or "Pipeline" in t for t in titulos), (
        f"Esperava recomendação de pipeline em {titulos}"
    )


# ---------------------------------------------------------------------------
# AT-004: concentração crítica (0.9) → componente concentracao_orgao <= 20
# ---------------------------------------------------------------------------

def test_at004_concentracao_critica():
    # 100 - (0.9 - 0.5)*200 = 100 - 80 = 20
    inp = _inputs_saudaveis(concentracao_orgao=0.9)
    result = calcular_score(inp)

    comp = _componente(result, "concentracao_orgao")
    assert comp.valor <= 20.0, (
        f"componente concentracao_orgao: esperado <= 20.0, obtido {comp.valor}"
    )


# ---------------------------------------------------------------------------
# AT-005: delta_semana == score_calculado - previous_score
# ---------------------------------------------------------------------------

def test_at005_delta_semana_calculado_corretamente():
    previous = 65
    inp = _inputs_saudaveis(previous_score=previous)
    result = calcular_score(inp)

    assert result.delta_semana is not None, "delta_semana não deve ser None quando previous_score é passado"
    assert result.delta_semana == result.score - previous, (
        f"delta_semana esperado {result.score - previous}, obtido {result.delta_semana}"
    )


def test_at005_delta_semana_none_sem_previous_score():
    inp = _inputs_saudaveis(previous_score=None)
    result = calcular_score(inp)

    assert result.delta_semana is None


# ---------------------------------------------------------------------------
# Extra: tenant sem dados → taxa_vitoria_90d == 50.0 (fallback neutro)
# ---------------------------------------------------------------------------

def test_extra_sem_runs_taxa_vitoria_fallback_neutro():
    inp = ScoreInputs(runs_ganhos_90d=0, runs_total_90d=0)
    result = calcular_score(inp)

    comp = _componente(result, "taxa_vitoria_90d")
    assert comp.valor == 50.0, (
        f"taxa_vitoria_90d sem dados: esperado 50.0, obtido {comp.valor}"
    )


# ---------------------------------------------------------------------------
# Extra: recomendações ordenadas por impacto_no_score desc, prioridade 1..n
# ---------------------------------------------------------------------------

def test_extra_recomendacoes_ordenadas_por_impacto_desc():
    # Força múltiplos componentes abaixo de 80 para gerar várias recomendações.
    inp = ScoreInputs(
        runs_ganhos_90d=2,
        runs_total_90d=10,
        tem_analise_recente_30d=False,
        certidoes_vencidas=1,
        empenhos_atrasados=1,
        concentracao_orgao=0.7,
    )
    result = calcular_score(inp)

    assert len(result.recomendacoes) >= 2, "Esperava ao menos 2 recomendações"

    impactos = [r.impacto_no_score for r in result.recomendacoes]
    assert impactos == sorted(impactos, reverse=True), (
        f"Recomendações não estão ordenadas por impacto desc: {impactos}"
    )

    prioridades = [r.prioridade for r in result.recomendacoes]
    assert prioridades == list(range(1, len(result.recomendacoes) + 1)), (
        f"Prioridades esperadas 1..{len(result.recomendacoes)}, obtidas {prioridades}"
    )


# ---------------------------------------------------------------------------
# Extra: estrutura — sempre 6 componentes, nomes corretos, pesos somam 1.0
# ---------------------------------------------------------------------------

NOMES_ESPERADOS = {
    "taxa_vitoria_90d",
    "pipeline_ativo",
    "contratos_em_dia",
    "certidoes_validas",
    "pagamentos_recebidos",
    "concentracao_orgao",
}


def test_extra_sempre_seis_componentes_com_nomes_corretos():
    inp = ScoreInputs()
    result = calcular_score(inp)

    assert len(result.componentes) == 6
    nomes = {c.nome for c in result.componentes}
    assert nomes == NOMES_ESPERADOS


def test_extra_pesos_somam_um():
    inp = ScoreInputs()
    result = calcular_score(inp)

    total_pesos = sum(c.peso for c in result.componentes)
    assert abs(total_pesos - 1.0) < 1e-9, f"Soma dos pesos: {total_pesos}"


# ---------------------------------------------------------------------------
# Extra: labels nos limiares exatos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("score_val,expected_label", [
    (80, "Excelente"),
    (60, "Bom"),
    (40, "Atenção"),
    (39, "Crítico"),
])
def test_extra_label_por_limiar(score_val: int, expected_label: str):
    """Verifica a função _label via score bruto fabricado com inputs controlados.

    Usa taxa_vitoria_90d (peso 0.25) e demais fixos para empurrar o score
    para o valor alvo. Como a função é pura e os pesos são conhecidos, basta
    verificar via _label diretamente.
    """
    from src.services.health_score import _label

    assert _label(score_val) == expected_label
