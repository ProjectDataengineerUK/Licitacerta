from __future__ import annotations

from datetime import date, datetime
from typing import Any

from src.portals.base import PortalAdapter, PortalFilter, RawEdital


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:19].replace("Z", ""))
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PNCPAdapter(PortalAdapter):
    """Adapter do PNCP — embrulha o PNCPClient existente na interface PortalAdapter."""

    portal_id = "pncp"
    portal_name = "Portal Nacional de Contratações Públicas"
    supports_api = True

    def __init__(self, client: Any) -> None:
        # client: src.api.pncp_client.PNCPClient (já aberto)
        self._client = client

    async def fetch_new_editals(
        self, since: datetime, filters: PortalFilter | None = None
    ) -> list[RawEdital]:
        data_final = date.today()
        raw = await self._client.search_publicacoes_all(since.date(), data_final)
        return [self._map(r) for r in raw]

    def _map(self, r: dict) -> RawEdital:
        orgao = r.get("orgaoEntidade") or {}
        return RawEdital(
            portal_id=self.portal_id,
            portal_edital_ref=r.get("numeroControlePNCP", ""),
            orgao_cnpj=(orgao.get("cnpj") if isinstance(orgao, dict) else None),
            objeto=r.get("objetoCompra", "") or "",
            valor_estimado_brl=_to_float(r.get("valorTotalEstimado")),
            data_publicacao=_parse_dt(r.get("dataPublicacaoPncp")),
            data_sessao=_parse_dt(r.get("dataAberturaProposta")),
            modalidade=r.get("modalidadeNome"),
            raw_data=r,
        )
