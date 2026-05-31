from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

_WS = re.compile(r"\s+")


def normalize_objeto(texto: str | None) -> str:
    """Normaliza o objeto para deduplicação: minúsculas, sem espaços redundantes."""
    return _WS.sub(" ", (texto or "").strip().lower())


def dedup_hash(
    *,
    orgao_cnpj: str | None,
    objeto: str | None,
    valor_estimado_brl: float | None,
    data_sessao: datetime | None,
) -> str:
    """SHA256 estável de (cnpj, objeto normalizado, valor, data da sessão).

    Mesmo edital publicado em portais diferentes produz o mesmo hash.
    """
    valor = f"{valor_estimado_brl:.2f}" if valor_estimado_brl is not None else ""
    sessao = data_sessao.date().isoformat() if data_sessao is not None else ""
    base = "|".join([
        (orgao_cnpj or "").strip(),
        normalize_objeto(objeto),
        valor,
        sessao,
    ])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


@dataclass
class RawEdital:
    """Edital normalizado, independente do portal de origem."""

    portal_id: str
    portal_edital_ref: str
    orgao_cnpj: str | None = None
    objeto: str = ""
    valor_estimado_brl: float | None = None
    data_publicacao: datetime | None = None
    data_sessao: datetime | None = None
    modalidade: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def dedup_hash(self) -> str:
        return dedup_hash(
            orgao_cnpj=self.orgao_cnpj,
            objeto=self.objeto,
            valor_estimado_brl=self.valor_estimado_brl,
            data_sessao=self.data_sessao,
        )


@dataclass
class PortalFilter:
    """Filtro de monitoramento aplicado por adapter."""

    segmentos: list[str] = field(default_factory=list)
    ufs: list[str] = field(default_factory=list)
    valor_min: float | None = None
    valor_max: float | None = None


@dataclass
class PortalHealthStatus:
    portal_id: str
    status: Literal["online", "offline", "error"]
    last_run: datetime | None = None
    last_error: str | None = None


class PortalAdapter(ABC):
    """Interface que todo portal deve implementar.

    Adicionar um novo portal = implementar esta interface, sem tocar no core.
    """

    portal_id: str = "unknown"
    portal_name: str = "Unknown"
    supports_api: bool = True

    @abstractmethod
    async def fetch_new_editals(
        self, since: datetime, filters: PortalFilter | None = None
    ) -> list[RawEdital]:
        """Editais novos desde ``since`` que casam com ``filters``."""

    async def health_check(self) -> PortalHealthStatus:
        """Verifica acessibilidade do portal. Default: tenta um fetch leve."""
        try:
            await self.fetch_new_editals(datetime.now(), PortalFilter())
            return PortalHealthStatus(portal_id=self.portal_id, status="online", last_run=datetime.now())
        except Exception as exc:  # noqa: BLE001 — health check reporta, não propaga
            return PortalHealthStatus(
                portal_id=self.portal_id,
                status="offline",
                last_error=f"{type(exc).__name__}: {exc}",
            )
