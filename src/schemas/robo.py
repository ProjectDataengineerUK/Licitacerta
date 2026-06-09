from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class EstrategiaLance(str, Enum):
    POR_POSICAO = "por_posicao"
    POR_MARGEM  = "por_margem"
    POR_VALOR   = "por_valor"


class ConfiguracaoRobo(BaseModel):
    run_id: str
    tenant_id: str
    estrategia: EstrategiaLance
    posicao_alvo: int = 1
    margem_minima_pct: float = 5.0
    valor_floor_brl: Decimal
    decremento_pct: float = 0.5
    intervalo_minimo_segundos: int = 20
    max_lances: int = 100
    portal_url: str = "https://www.comprasnet.gov.br"


class Lance(BaseModel):
    numero: int
    valor_brl: Decimal
    posicao_resultante: int | None = None
    timestamp_utc: str
    motivo: Literal["estrategia", "reacao", "manual"] = "estrategia"
    aprovado_hitl: bool = False


class SessaoResult(BaseModel):
    session_id: str
    run_id: str
    tenant_id: str
    status: Literal["em_andamento", "encerrada", "suspensa_hitl", "erro"]
    lances: list[Lance] = []
    posicao_final: int | None = None
    valor_final_brl: Decimal | None = None
    motivo_encerramento: str | None = None
