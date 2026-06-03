"""SCORE_SAUDE_OPERACAO — cálculo do score de saúde operacional (0–100).

Função pura: recebe indicadores agregados (ScoreInputs) e devolve HealthScore
com componentes, label e recomendações ordenadas por ganho potencial.
"""
from __future__ import annotations

from src.schemas.health import (
    ComponenteScore,
    ComponenteStatus,
    HealthScore,
    Recomendacao,
    ScoreInputs,
    ScoreLabel,
)

# nome → (peso, descrição)
COMPONENTES: dict[str, tuple[float, str]] = {
    "taxa_vitoria_90d": (0.25, "Taxa de vitória nos últimos 90 dias"),
    "pipeline_ativo": (0.20, "Há novas oportunidades entrando?"),
    "contratos_em_dia": (0.20, "Contratos próximos do vencimento sem ação"),
    "certidoes_validas": (0.15, "Certidões vencendo ou vencidas"),
    "pagamentos_recebidos": (0.10, "Empenhos pagos no prazo (sem atrasos)"),
    "concentracao_orgao": (0.10, "Risco de dependência de um órgão"),
}

# recomendação por componente: (titulo, acao, link)
_RECO = {
    "taxa_vitoria_90d": ("Taxa de vitória baixa", "Revise precificação e critérios de bid/no-bid", "/pipeline"),
    "pipeline_ativo": ("Pipeline parado", "Analise novos editais compatíveis", "/"),
    "contratos_em_dia": ("Contratos vencendo", "Renove ou encerre contratos próximos do vencimento", "/contratos"),
    "certidoes_validas": ("Certidões a regularizar", "Renove certidões vencendo/vencidas", "/certidoes"),
    "pagamentos_recebidos": ("Pagamentos atrasados", "Cobre empenhos atrasados / gere notificação", "/financeiro"),
    "concentracao_orgao": ("Concentração em um órgão", "Diversifique os órgãos compradores", "/pipeline"),
}


def _label(score: float) -> ScoreLabel:
    if score >= 80:
        return "Excelente"
    if score >= 60:
        return "Bom"
    if score >= 40:
        return "Atenção"
    return "Crítico"


def _status(valor: float) -> ComponenteStatus:
    if valor >= 80:
        return "otimo"
    if valor >= 60:
        return "bom"
    if valor >= 40:
        return "atencao"
    return "critico"


def _valores(inp: ScoreInputs) -> dict[str, float]:
    taxa = (inp.runs_ganhos_90d / inp.runs_total_90d * 100) if inp.runs_total_90d > 0 else 50.0
    return {
        "taxa_vitoria_90d": taxa,
        "pipeline_ativo": 100.0 if inp.tem_analise_recente_30d else 20.0,
        "contratos_em_dia": max(0.0, 100.0 - inp.contratos_criticos * 25),
        "certidoes_validas": max(0.0, 100.0 - inp.certidoes_vencendo_15d * 10 - inp.certidoes_vencidas * 30),
        "pagamentos_recebidos": max(0.0, 100.0 - inp.empenhos_atrasados * 20),
        "concentracao_orgao": 100.0 if inp.concentracao_orgao < 0.5
        else max(0.0, 100.0 - (inp.concentracao_orgao - 0.5) * 200),
    }


def calcular_score(inputs: ScoreInputs) -> HealthScore:
    valores = _valores(inputs)

    componentes: list[ComponenteScore] = []
    total = 0.0
    for nome, (peso, desc) in COMPONENTES.items():
        valor = round(valores[nome], 1)
        contrib = valor * peso
        total += contrib
        componentes.append(ComponenteScore(
            nome=nome, valor=valor, peso=peso, contribuicao=round(contrib, 2),
            descricao=desc, status=_status(valor),
        ))

    score = round(total)

    recomendacoes: list[Recomendacao] = []
    for nome, (peso, _desc) in COMPONENTES.items():
        valor = valores[nome]
        if valor < 80:
            titulo, acao, link = _RECO[nome]
            recomendacoes.append(Recomendacao(
                prioridade=0,
                titulo=titulo, acao=acao, link=link,
                impacto_no_score=round((100 - valor) * peso, 1),
            ))
    recomendacoes.sort(key=lambda r: r.impacto_no_score, reverse=True)
    for i, r in enumerate(recomendacoes, start=1):
        r.prioridade = i

    delta = None
    if inputs.previous_score is not None:
        delta = score - inputs.previous_score

    return HealthScore(
        score=score,
        label=_label(score),  # consistente com o int exibido (E1)
        componentes=componentes,
        recomendacoes=recomendacoes,
        delta_semana=delta,
    )
