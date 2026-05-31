"""PRECIFICACAO_AVANCADA — carga tributária por regime.

Cálculos determinísticos. As alíquotas do Simples Nacional são mantidas como
configuração (faixas do Anexo III — serviços) para facilitar atualização anual
(Resolução CGSN). Disclaimer de produto: sempre orientar "consulte seu contador".
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.schemas.results import ImpostoResult

# Anexo III (serviços) — (limite_superior_receita_anual, alíquota efetiva simplificada)
_SIMPLES_SERVICOS: list[tuple[Decimal, Decimal]] = [
    (Decimal("180000"), Decimal("0.06")),
    (Decimal("360000"), Decimal("0.112")),
    (Decimal("720000"), Decimal("0.135")),
    (Decimal("1800000"), Decimal("0.16")),
    (Decimal("3600000"), Decimal("0.21")),
    (Decimal("4800000"), Decimal("0.33")),
]

_LUCRO_PRESUMIDO_SERVICOS = {
    "pis": Decimal("0.0065"),
    "cofins": Decimal("0.03"),
    "csll": Decimal("0.0288"),  # 32% × 9%
    "irpj": Decimal("0.048"),   # 32% × 15%
}

_CENT = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _aliquota_simples(faturamento_anual: Decimal | None) -> Decimal:
    fat = faturamento_anual if faturamento_anual is not None else Decimal("0")
    for limite, aliquota in _SIMPLES_SERVICOS:
        if fat <= limite:
            return aliquota
    return _SIMPLES_SERVICOS[-1][1]


def calcular_impostos(
    valor_contrato: Decimal,
    regime: str,
    segmento: str = "servicos",
    faturamento_anual: Decimal | None = None,
    iss_pct: Decimal = Decimal("0.05"),
) -> ImpostoResult:
    """Carga tributária sobre o contrato.

    Suporta ``simples`` e ``lucro_presumido`` (serviços). ``lucro_real`` depende
    do lucro contábil e deve ser apurado pelo contador.
    """
    regime = regime.lower()

    if regime == "simples":
        aliquota = _aliquota_simples(faturamento_anual)
        valor = _q(valor_contrato * aliquota)
        return ImpostoResult(
            regime="simples",
            aliquota_total_pct=float(aliquota * 100),
            valor_impostos_brl=valor,
            detalhamento={"simples_nacional": valor},
        )

    if regime == "lucro_presumido":
        componentes = dict(_LUCRO_PRESUMIDO_SERVICOS)
        componentes["iss"] = iss_pct
        detalhamento = {nome: _q(valor_contrato * aliq) for nome, aliq in componentes.items()}
        total_aliq = sum(componentes.values(), Decimal("0"))
        return ImpostoResult(
            regime="lucro_presumido",
            aliquota_total_pct=float(total_aliq * 100),
            valor_impostos_brl=_q(valor_contrato * total_aliq),
            detalhamento=detalhamento,
        )

    raise ValueError(
        "regime 'lucro_real' depende do lucro contábil — apure com seu contador; "
        "use 'simples' ou 'lucro_presumido'"
    )
