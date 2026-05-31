"""GESTAO_CONTRATOS_FULL — cálculo de reajuste contratual via índices IBGE.

Compõe a variação mensal do índice (IPCA/INPC) entre a data base e a data de
reajuste. Fonte pública: servicodados.ibge.gov.br/api/v3/agregados.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

_IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
# agregado por índice; variável 63 = variação mensal (%)
_AGREGADO = {"IPCA": "1737", "INPC": "1736"}
_VARIAVEL = "63"

_INDICES_SUPORTADOS = tuple(_AGREGADO.keys())


@dataclass
class ReajusteResult:
    valor_base_brl: Decimal
    novo_valor_brl: Decimal
    variacao_pct: float
    indice: str
    data_base: date
    data_reajuste: date
    fonte: str = "IBGE"
    data_consulta: datetime | None = None


def _periodo(d: date) -> str:
    return f"{d.year}{d.month:02d}"


def _parse_serie(payload: Any) -> dict[str, float]:
    """Extrai {periodo: variacao_pct} da resposta v3/agregados do IBGE."""
    try:
        serie = payload[0]["resultados"][0]["series"][0]["serie"]
    except (KeyError, IndexError, TypeError):
        return {}
    out: dict[str, float] = {}
    for periodo, valor in serie.items():
        try:
            out[periodo] = float(valor)
        except (TypeError, ValueError):
            continue  # IBGE usa "..." ou "-" para indisponível
    return out


class ReajusteService:
    """Calcula reajuste compondo a variação mensal do índice.

    O cliente httpx é injetável para testes (MockTransport).
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns = client is None
        self._cache: dict[tuple[str, str, str], dict[str, float]] = {}

    async def __aenter__(self) -> ReajusteService:
        if self._owns:
            self._client = httpx.AsyncClient(timeout=20.0)
        return self

    async def __aexit__(self, *_) -> None:
        if self._owns and self._client:
            await self._client.aclose()
            self._client = None

    async def calcular(
        self,
        valor_base: Decimal,
        indice: str,
        data_base: date,
        data_reajuste: date,
    ) -> ReajusteResult:
        indice = indice.upper()
        if indice not in _AGREGADO:
            raise ValueError(
                f"índice {indice!r} não suportado via IBGE (use {', '.join(_INDICES_SUPORTADOS)})"
            )
        if data_reajuste <= data_base:
            raise ValueError("data_reajuste deve ser posterior à data_base")

        serie = await self._fetch_serie(indice, data_base, data_reajuste)
        # compõe meses estritamente após a data base até a data de reajuste (inclusive)
        fator = Decimal("1")
        for periodo in sorted(serie):
            if _periodo(data_base) < periodo <= _periodo(data_reajuste):
                fator *= Decimal("1") + Decimal(str(serie[periodo])) / Decimal("100")

        novo_valor = (valor_base * fator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        variacao = (fator - Decimal("1")) * Decimal("100")
        return ReajusteResult(
            valor_base_brl=valor_base,
            novo_valor_brl=novo_valor,
            variacao_pct=float(variacao.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
            indice=indice,
            data_base=data_base,
            data_reajuste=data_reajuste,
            data_consulta=datetime.now(),
        )

    async def _fetch_serie(self, indice: str, data_base: date, data_reajuste: date) -> dict[str, float]:
        assert self._client is not None, "ReajusteService deve ser usado como async context manager"
        key = (indice, _periodo(data_base), _periodo(data_reajuste))
        if key in self._cache:
            return self._cache[key]
        agregado = _AGREGADO[indice]
        url = (
            f"{_IBGE_BASE}/{agregado}/periodos/"
            f"{_periodo(data_base)}-{_periodo(data_reajuste)}/variaveis/{_VARIAVEL}"
        )
        resp = await self._client.get(url, params={"localidades": "N1[all]"})
        resp.raise_for_status()
        serie = _parse_serie(resp.json())
        self._cache[key] = serie
        return serie
