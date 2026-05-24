from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Empresa elegível — edital padrão sem restrições",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de material de escritório",
                orgao="Secretaria Municipal de Administração",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CND Estadual", "FGTS"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("30000.00"),
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_is_eligible": True,
        "expected_has_blocking": False,
    },
    {
        "id": "eval-002",
        "description": "Empresa inelegível — exigência técnica de engenharia pesada inacessível para PME de TI",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Construção de ponte metálica com estruturas especiais",
                orgao="Departamento de Infraestrutura Estadual",
                modalidade="concorrencia",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "CND Federal",
                    "Registro no CREA",
                    "Acervo técnico de obras de arte especiais",
                ],
                exigencias_tecnicas=[
                    "Responsável técnico com Acervo Técnico em construção de pontes metálicas",
                    "Atestado de execução de pontes com vão superior a 50 metros",
                ],
                penalidades=["Multa de 10% por atraso"],
                valor_estimado=Decimal("5000000.00"),
                garantia_exigida=True,
                garantia_percentual=5.0,
                prazo_entrega_dias=720,
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_is_eligible": False,
        "expected_has_blocking": True,
    },
    {
        "id": "eval-003",
        "description": "Elegível com múltiplas certidões — expiring_certifications esperadas",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Prestação de serviços de limpeza e conservação predial",
                orgao="Tribunal Regional do Trabalho",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "CND Federal (RFB + PGFN)",
                    "CND Estadual",
                    "CND Municipal",
                    "Certificado de Regularidade do FGTS",
                    "Certidão Negativa de Débitos Trabalhistas (CNDT)",
                ],
                exigencias_tecnicas=[],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("120000.00"),
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_is_eligible": True,
        "expected_has_blocking": False,
    },
    {
        "id": "eval-004",
        "description": "Inelegível — capital mínimo e faturamento mínimo desproporcionais (art. 69 §1º)",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de refeições industriais para servidores",
                orgao="Autarquia Federal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "Balanço patrimonial com patrimônio líquido mínimo de R$ 1.000.000",
                    "Comprovante de faturamento mínimo de R$ 10.000.000 nos últimos 12 meses",
                ],
                exigencias_tecnicas=[],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("200000.00"),
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_is_eligible": False,
        "expected_has_blocking": True,
    },
    {
        "id": "eval-005",
        "description": "Edital de TI — exigências compatíveis com PME de tecnologia",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Desenvolvimento e manutenção de sistema de gestão municipal",
                orgao="Câmara Municipal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "CND Federal",
                    "Atestado de fornecimento de sistema de informação para órgão público",
                ],
                exigencias_tecnicas=[
                    "Profissional com experiência comprovada em desenvolvimento web",
                ],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("80000.00"),
            ),
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_is_eligible": True,
        "expected_has_blocking": False,
    },
]
