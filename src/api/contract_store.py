"""GESTAO_CONTRATOS_FULL — modelos + store em memória de contratos.

Espelha o padrão in-memory do RunStore. A persistência em AlloyDB
(`scripts/migrations/00X_contracts.sql`) é uma evolução futura; a interface aqui
já isola o domínio para essa troca.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

TipoContrato = Literal["contrato", "ata_srp", "empenho_direto"]
StatusContrato = Literal["ativo", "vencido", "encerrado", "renovado"]
StatusEmpenho = Literal["emitido", "liquidado", "pago", "cancelado"]
StatusConvocacao = Literal["pendente", "atendida", "rejeitada"]


# --------------------------------------------------------------------------- #
# Input models
# --------------------------------------------------------------------------- #
class ContractCreate(BaseModel):
    orgao_cnpj: str
    orgao_nome: str = ""
    objeto: str = ""
    tipo: TipoContrato = "contrato"
    valor_original_brl: float = 0.0
    indice_reajuste: str | None = None
    data_base: date | None = None
    data_inicio: date
    data_vencimento: date
    numero_contrato: str | None = None
    run_id: str | None = None
    prazo_pagamento_dias: int = 30
    srp_quantidade_registrada: float | None = None


class ContractPatch(BaseModel):
    valor_atual_brl: float | None = None
    data_vencimento: date | None = None
    status: StatusContrato | None = None
    numero_contrato: str | None = None


class EmpenhoCreate(BaseModel):
    numero_empenho: str
    valor_brl: float
    data_emissao: date
    observacoes: str = ""


class EmpenhoPatch(BaseModel):
    status: StatusEmpenho | None = None
    data_liquidacao: date | None = None
    data_pagamento: date | None = None


class ConvocacaoCreate(BaseModel):
    numero_convocacao: str
    quantidade: float
    valor_unitario_brl: float = 0.0
    data_convocacao: date | None = None
    status: StatusConvocacao = "pendente"


# --------------------------------------------------------------------------- #
# Output models
# --------------------------------------------------------------------------- #
class Empenho(BaseModel):
    id: str
    numero_empenho: str
    valor_brl: float
    data_emissao: date
    data_liquidacao: date | None = None
    data_pagamento: date | None = None
    status: StatusEmpenho = "emitido"
    observacoes: str = ""


class Convocacao(BaseModel):
    id: str
    numero_convocacao: str
    quantidade: float
    valor_unitario_brl: float = 0.0
    data_convocacao: date | None = None
    status: StatusConvocacao = "pendente"


class Contract(BaseModel):
    id: str
    tenant_id: str | None = None
    run_id: str | None = None
    numero_contrato: str | None = None
    orgao_cnpj: str
    orgao_nome: str = ""
    objeto: str = ""
    tipo: TipoContrato = "contrato"
    valor_original_brl: float = 0.0
    valor_atual_brl: float = 0.0
    indice_reajuste: str | None = None
    data_base: date | None = None
    data_inicio: date
    data_vencimento: date
    status: StatusContrato = "ativo"
    prazo_pagamento_dias: int = 30
    srp_quantidade_registrada: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    empenhos: list[Empenho] = []
    convocacoes: list[Convocacao] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def saldo_srp(self) -> float | None:
        if self.srp_quantidade_registrada is None:
            return None
        atendidas = sum(c.quantidade for c in self.convocacoes if c.status == "atendida")
        return self.srp_quantidade_registrada - atendidas


class ContractStore:
    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}
        self._lock = asyncio.Lock()

    async def create(self, body: ContractCreate, tenant_id: str | None = None) -> Contract:
        async with self._lock:
            cid = str(uuid.uuid4())
            contract = Contract(
                id=cid,
                tenant_id=tenant_id,
                valor_atual_brl=body.valor_original_brl,
                **body.model_dump(),
            )
            self._contracts[cid] = contract
            return contract

    async def get(self, cid: str) -> Contract | None:
        async with self._lock:
            return self._contracts.get(cid)

    async def list(self, status: str | None = None) -> list[Contract]:
        async with self._lock:
            items = list(self._contracts.values())
        if status:
            items = [c for c in items if c.status == status]
        return items

    async def patch(self, cid: str, body: ContractPatch) -> Contract | None:
        async with self._lock:
            c = self._contracts.get(cid)
            if c is None:
                return None
            for key, value in body.model_dump(exclude_none=True).items():
                setattr(c, key, value)
            return c

    async def delete(self, cid: str) -> bool:
        async with self._lock:
            c = self._contracts.get(cid)
            if c is None:
                return False
            c.status = "encerrado"
            return True

    async def add_empenho(self, cid: str, body: EmpenhoCreate) -> Empenho | None:
        async with self._lock:
            c = self._contracts.get(cid)
            if c is None:
                return None
            emp = Empenho(id=str(uuid.uuid4()), **body.model_dump())
            c.empenhos.append(emp)
            return emp

    async def patch_empenho(self, cid: str, eid: str, body: EmpenhoPatch) -> Empenho | None:
        async with self._lock:
            c = self._contracts.get(cid)
            if c is None:
                return None
            emp = next((e for e in c.empenhos if e.id == eid), None)
            if emp is None:
                return None
            for key, value in body.model_dump(exclude_none=True).items():
                setattr(emp, key, value)
            return emp

    async def add_convocacao(self, cid: str, body: ConvocacaoCreate) -> Convocacao | None:
        async with self._lock:
            c = self._contracts.get(cid)
            if c is None:
                return None
            conv = Convocacao(id=str(uuid.uuid4()), **body.model_dump())
            c.convocacoes.append(conv)
            return conv
