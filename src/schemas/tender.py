from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Evidence(BaseModel):
    document: str
    page: int
    excerpt: str


class PageContent(BaseModel):
    page_number: int
    text: str
    tables: list[dict]
    is_ocr: bool


class TenderSchema(BaseModel):
    objeto: str
    orgao: str
    modalidade: str
    data_abertura: date | None = None
    data_encerramento: date | None = None
    valor_estimado: Decimal | None = None
    criterio_julgamento: str
    documentos_exigidos: list[str]
    exigencias_tecnicas: list[str]
    penalidades: list[str]
    garantia_exigida: bool = False
    garantia_percentual: float | None = None
    prazo_entrega_dias: int | None = None
    prazo_pagamento_dias: int | None = None
    evidence: list[Evidence] = []
