"""PRECIFICACAO_AVANCADA — BDI para obras (TCU, Acórdão 2.369/2011).

Fórmula: BDI = [ (1 + AC + S + R + G) / (1 - DF - L - I) - 1 ] × 100
AC=Adm. Central, S=Seguros, R=Riscos, G=Garantia, DF=Desp. Financeiras,
L=Lucro, I=Impostos (PIS+COFINS+ISS).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.schemas.results import BDIResult

_CENT = Decimal("0.01")


def calcular_bdi_obras(
    administracao_central_pct: float = 5.0,
    lucro_pct: float = 7.4,
    riscos_pct: float = 0.97,
    seguros_pct: float = 0.08,
    garantia_pct: float = 0.0,
    despesas_financeiras_pct: float = 0.5,
    impostos_pct: float = 8.65,
    custo_direto_brl: Decimal | None = None,
) -> BDIResult:
    ac = Decimal(str(administracao_central_pct)) / 100
    s = Decimal(str(seguros_pct)) / 100
    r = Decimal(str(riscos_pct)) / 100
    g = Decimal(str(garantia_pct)) / 100
    df = Decimal(str(despesas_financeiras_pct)) / 100
    lucro = Decimal(str(lucro_pct)) / 100
    impostos = Decimal(str(impostos_pct)) / 100

    denominador = Decimal("1") - df - lucro - impostos
    if denominador <= 0:
        raise ValueError("DF + Lucro + Impostos não pode ser >= 100%")

    bdi_fator = (Decimal("1") + ac + s + r + g) / denominador - Decimal("1")
    bdi_pct = float((bdi_fator * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    valor_bdi = None
    if custo_direto_brl is not None:
        valor_bdi = (custo_direto_brl * bdi_fator).quantize(_CENT, rounding=ROUND_HALF_UP)

    return BDIResult(
        bdi_pct=bdi_pct,
        valor_bdi_brl=valor_bdi,
        composicao={
            "administracao_central": administracao_central_pct,
            "lucro": lucro_pct,
            "riscos": riscos_pct,
            "seguros": seguros_pct,
            "garantia": garantia_pct,
            "despesas_financeiras": despesas_financeiras_pct,
            "impostos": impostos_pct,
        },
    )
