"""Portfolio optimizer — deterministic knapsack greedy (no LLM)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from src.schemas.portfolio import (
    Oportunidade,
    PortfolioOtimizacaoInput,
    PortfolioOtimizacaoResult,
    ResultadoCenario,
)

NomeCenario = Literal["Conservador", "Moderado", "Agressivo"]

CENARIOS: dict[NomeCenario, dict] = {
    "Conservador": {"capital_max_pct": 0.50, "prob_minima": 0.60, "max_contratos": 3},
    "Moderado":    {"capital_max_pct": 0.70, "prob_minima": 0.40, "max_contratos": 5},
    "Agressivo":   {"capital_max_pct": 0.90, "prob_minima": 0.20, "max_contratos": 8},
}


def otimizar(data: PortfolioOtimizacaoInput) -> PortfolioOtimizacaoResult:
    cenarios: dict[NomeCenario, ResultadoCenario] = {}
    todos_selecionados: set[str] = set()

    for nome, params in CENARIOS.items():
        candidatas = [
            op for op in data.oportunidades
            if op.probabilidade_vitoria_pct / 100 >= params["prob_minima"]
        ]
        capital_max = float(data.capital_giro_disponivel_brl) * params["capital_max_pct"]
        cap_disponivel = data.capacidade_maxima_pct - data.capacidade_atual_pct

        selecionadas = _knapsack_greedy(
            candidatas,
            capital_max=capital_max,
            capacidade_max=cap_disponivel,
            max_contratos=min(params["max_contratos"], data.max_contratos_simultaneos),
        )
        todos_selecionados.update(op.run_id for op in selecionadas)
        cenarios[nome] = _calcular_resultado(nome, selecionadas)  # type: ignore[arg-type]

    rejeitadas = [
        op.run_id for op in data.oportunidades
        if op.run_id not in todos_selecionados
    ]

    return PortfolioOtimizacaoResult(
        conservador=cenarios["Conservador"],
        moderado=cenarios["Moderado"],
        agressivo=cenarios["Agressivo"],
        oportunidades_rejeitadas=rejeitadas,
        resumo=_gerar_resumo(cenarios),
    )


def _eficiencia(op: Oportunidade) -> float:
    val_esperado = float(op.valor_estimado_brl) * (op.probabilidade_vitoria_pct / 100)
    return val_esperado / max(float(op.custo_estimado_brl), 1.0)


def _knapsack_greedy(
    candidatas: list[Oportunidade],
    capital_max: float,
    capacidade_max: float,
    max_contratos: int,
) -> list[Oportunidade]:
    ordenadas = sorted(candidatas, key=_eficiencia, reverse=True)
    selecionadas: list[Oportunidade] = []
    capital_usado = 0.0
    cap_usada = 0.0

    for op in ordenadas:
        if len(selecionadas) >= max_contratos:
            break
        novo_capital = capital_usado + float(op.custo_estimado_brl)
        nova_cap = cap_usada + op.capacidade_necessaria_pct
        if novo_capital <= capital_max and nova_cap <= capacidade_max:
            selecionadas.append(op)
            capital_usado = novo_capital
            cap_usada = nova_cap

    return selecionadas


def _calcular_resultado(nome: NomeCenario, selecionadas: list[Oportunidade]) -> ResultadoCenario:
    if not selecionadas:
        return ResultadoCenario(
            nome=nome,
            oportunidades_selecionadas=[],
            valor_total_brl=Decimal(0),
            custo_total_brl=Decimal(0),
            capital_comprometido_brl=Decimal(0),
            valor_esperado_ponderado_brl=Decimal(0),
            probabilidade_vitoria_media_pct=0.0,
            capacidade_utilizada_pct=0.0,
            roi_esperado_pct=0.0,
        )

    val_total = sum(op.valor_estimado_brl for op in selecionadas)
    custo_total = sum(op.custo_estimado_brl for op in selecionadas)
    val_esperado = sum(
        op.valor_estimado_brl * Decimal(str(op.probabilidade_vitoria_pct / 100))
        for op in selecionadas
    )
    prob_media = sum(op.probabilidade_vitoria_pct for op in selecionadas) / len(selecionadas)
    cap = sum(op.capacidade_necessaria_pct for op in selecionadas)
    roi = float((val_esperado - custo_total) / custo_total * 100) if custo_total > 0 else 0.0

    return ResultadoCenario(
        nome=nome,
        oportunidades_selecionadas=[op.run_id for op in selecionadas],
        valor_total_brl=val_total,
        custo_total_brl=custo_total,
        capital_comprometido_brl=custo_total,
        valor_esperado_ponderado_brl=val_esperado,
        probabilidade_vitoria_media_pct=prob_media,
        capacidade_utilizada_pct=cap,
        roi_esperado_pct=roi,
    )


def _gerar_resumo(cenarios: dict[NomeCenario, ResultadoCenario]) -> str:
    partes: list[str] = []
    for nome, c in cenarios.items():
        n = len(c.oportunidades_selecionadas)
        val = float(c.valor_esperado_ponderado_brl)
        roi = c.roi_esperado_pct
        partes.append(f"{nome}: {n} licitação(ões), VE R$ {val:,.0f}, ROI {roi:.0f}%")
    return " | ".join(partes)
