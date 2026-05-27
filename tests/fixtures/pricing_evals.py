from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

_TENDER_TI = TenderSchema(
    objeto="Desenvolvimento de sistema de gestão de contratos",
    orgao="Tribunal Regional Federal 3ª Região",
    modalidade="pregao_eletronico",
    criterio_julgamento="menor_preco",
    documentos_exigidos=["CNPJ ativo", "CND Federal", "Atestado técnico"],
    exigencias_tecnicas=["Profissional com experiência em desenvolvimento web"],
    penalidades=["Multa de 2% por atraso"],
    valor_estimado=Decimal("300000.00"),
    prazo_entrega_dias=90,
    prazo_pagamento_dias=30,
)

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Serviço de TI — margem confortável esperada acima de 15%",
        "context": {
            "tender_schema": _TENDER_TI,
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_margin_min": 10.0,
        "expected_has_price": True,
    },
    {
        "id": "eval-002",
        "description": "Obra pública com custo alto — margem reduzida esperada",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Pavimentação asfáltica em vias urbanas — 5 km",
                orgao="Prefeitura Municipal de Campinas",
                modalidade="concorrencia",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CREA", "Balanço patrimonial"],
                exigencias_tecnicas=["RT com acervo técnico em pavimentação"],
                penalidades=["Multa de 10% por rescisão"],
                valor_estimado=Decimal("8000000.00"),
                garantia_exigida=True,
                garantia_percentual=5.0,
                prazo_entrega_dias=365,
                prazo_pagamento_dias=30,
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_margin_min": 3.0,
        "expected_has_price": True,
    },
    {
        "id": "eval-003",
        "description": "Fornecimento com prazo de pagamento longo (60 dias) — impacto financeiro",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de uniformes para servidores públicos",
                orgao="Secretaria de Administração Estadual",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("150000.00"),
                prazo_entrega_dias=45,
                prazo_pagamento_dias=60,
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_margin_min": 5.0,
        "expected_has_price": True,
    },
    {
        "id": "eval-004",
        "description": "Serviço de limpeza — mercado competitivo, margem apertada",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Prestação continuada de serviços de limpeza e conservação",
                orgao="Câmara dos Deputados",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CNDT"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("600000.00"),
                prazo_entrega_dias=365,
                prazo_pagamento_dias=30,
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_margin_min": 2.0,
        "expected_has_price": True,
    },
]
