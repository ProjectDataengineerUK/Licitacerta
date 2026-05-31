"""Schemas de tenant — perfil financeiro para precificação avançada."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class TenantFinancialProfile(BaseModel):
    regime_tributario: Literal["simples", "lucro_presumido", "lucro_real"] = "simples"
    faturamento_anual_brl: Decimal | None = None
    limite_credito_brl: Decimal | None = None
    taxa_desconto_interna_pct: float = 12.0
    municipio_sede: str | None = None
    iss_pct: float = 5.0
    tem_obras: bool = False
