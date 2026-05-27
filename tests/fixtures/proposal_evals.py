from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Proposta de TI — deve gerar proposta estruturada com preço",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Desenvolvimento e implantação de sistema de ouvidoria municipal",
                orgao="Prefeitura de Ribeirão Preto",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "Atestado técnico"],
                exigencias_tecnicas=["Profissional com experiência em desenvolvimento web"],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("180000.00"),
                prazo_entrega_dias=60,
                prazo_pagamento_dias=30,
            ),
            "bid_decision": {"recommendation": "participar", "expected_margin_pct": 20.0},
        },
        "expected_has_content": True,
        "expected_has_price": True,
    },
    {
        "id": "eval-002",
        "description": "Proposta de fornecimento — descrição técnica e preço unitário",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de 200 cadeiras ergonômicas para escritório",
                orgao="Tribunal Regional Eleitoral",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CND Estadual"],
                exigencias_tecnicas=["Produto com certificação ABNT"],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("60000.00"),
                prazo_entrega_dias=30,
                prazo_pagamento_dias=30,
            ),
            "bid_decision": {"recommendation": "participar", "expected_margin_pct": 15.0},
        },
        "expected_has_content": True,
        "expected_has_price": True,
    },
    {
        "id": "eval-003",
        "description": "Proposta de serviço continuado — validade de 90 dias",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Prestação de serviços de manutenção de equipamentos de impressão",
                orgao="Controladoria-Geral da União",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal"],
                exigencias_tecnicas=["Técnico certificado pelo fabricante"],
                penalidades=["Multa de 2% por dia de atraso"],
                valor_estimado=Decimal("96000.00"),
                prazo_entrega_dias=365,
                prazo_pagamento_dias=30,
            ),
            "bid_decision": {"recommendation": "participar", "expected_margin_pct": 18.0},
        },
        "expected_has_content": True,
        "expected_has_price": True,
    },
]
