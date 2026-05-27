from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Oportunidade clara — TI PME sem restrições, margem boa",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Suporte técnico e manutenção de sistemas de informação",
                orgao="Câmara Municipal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "Atestado técnico"],
                exigencias_tecnicas=["Profissional certificado em suporte de TI"],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("120000.00"),
                prazo_pagamento_dias=30,
            ),
        },
        "expected_recommendation_in": ["participar", "participar_com_ressalvas"],
    },
    {
        "id": "eval-002",
        "description": "Edital com cláusula crítica — deve recomendar impugnar ou não participar",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Serviços de consultoria em tecnologia da informação",
                orgao="Autarquia Federal de Regulação",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "Certidão de capacidade técnica emitida por entidade privada sem previsão legal",
                    "Declaração de inexistência de processos trabalhistas nos últimos 10 anos",
                ],
                exigencias_tecnicas=[],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("200000.00"),
            ),
        },
        "expected_recommendation_in": ["impugnar", "nao_participar", "pedir_esclarecimento"],
    },
    {
        "id": "eval-003",
        "description": "Obra de engenharia pesada inacessível — não participar",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Construção de ponte metálica sobre o Rio Tietê — vão de 80 metros",
                orgao="Departamento de Estradas de Rodagem",
                modalidade="concorrencia",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "Registro no CREA",
                    "Acervo técnico de pontes metálicas com vão superior a 50 metros",
                ],
                exigencias_tecnicas=[
                    "Responsável técnico com acervo técnico em pontes metálicas",
                    "Atestado de execução de pontes similares",
                ],
                penalidades=["Multa de 10% por atraso"],
                valor_estimado=Decimal("25000000.00"),
                garantia_exigida=True,
                garantia_percentual=5.0,
                prazo_entrega_dias=720,
            ),
        },
        "expected_recommendation_in": ["nao_participar"],
    },
    {
        "id": "eval-004",
        "description": "Edital de material de escritório — participar sem ressalvas",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Aquisição de material de escritório (papel A4, canetas, envelopes)",
                orgao="Câmara Municipal de Santos",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CND Estadual"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 2% por atraso, limitada a 10%"],
                valor_estimado=Decimal("18000.00"),
                prazo_pagamento_dias=30,
            ),
        },
        "expected_recommendation_in": ["participar"],
    },
    {
        "id": "eval-005",
        "description": "Margem questionável com prazo de pagamento 90 dias — ressalvas esperadas",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de gêneros alimentícios para cantina escolar",
                orgao="Secretaria de Educação Municipal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "Alvará sanitário", "CND Federal"],
                exigencias_tecnicas=["Licença ANVISA para produtos alimentícios"],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("80000.00"),
                prazo_pagamento_dias=90,
            ),
        },
        "expected_recommendation_in": ["participar_com_ressalvas", "participar", "pedir_esclarecimento"],
    },
]
