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


class TenderVerticalMatch(BaseModel):
    vertical_detectada: str | None = None
    score_compatibilidade: float = 0.5  # 0.0 a 1.0
    alerta_fora_do_setor: bool = False
    motivo: str | None = None


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
    # Direcionamento signals
    especificacao_tem_marca: bool = False
    exige_modelo_especifico: bool = False
    atestado_cnae_restritivo: bool = False
    atestado_valor_elevado: bool = False
    certidao_nao_padrao: bool = False
    prazo_proposta_dias: int | None = None
    data_publicacao: date | None = None
    visita_tecnica_obrigatoria: bool = False
    prazo_visita_dias: int | None = None
    valor_referencia_coincide_historico: bool = False
    restringe_me_epp: bool = False
    justificativa_restricao: str | None = None
    # Pregoeiro
    pregoeiro_nome: str | None = None
    # Extra fields used by agents
    uasg: str | None = None
    orgao_cnpj: str | None = None
    segmento_cnae: str | None = None
    catmat_code: str | None = None
    numero: str | None = None
    tipo_objeto: str = "produto"
    duracao_meses: int | None = None
    fornecedor_nome: str | None = None
    fornecedor_cnpj: str | None = None
