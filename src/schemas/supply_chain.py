from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CheckStatus = Literal["aprovado", "reprovado", "nao_verificado", "pendente_regularizacao"]


class APICheck(BaseModel):
    api: str
    status: CheckStatus
    numero_registro: str | None = None
    valido_ate: str | None = None
    nota: str | None = None


class SupplyChainCheckResult(BaseModel):
    produto_descricao: str
    fabricante_nome: str
    fabricante_cnpj: str
    categoria: str
    checks: list[APICheck]
    status_geral: CheckStatus
    bloqueante: bool
    fundamentacao: str | None = None
