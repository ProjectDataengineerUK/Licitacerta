from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Especificação de marca — alto risco (ESPECIFICACAO_MARCA)",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Aquisição de notebooks para uso administrativo",
                orgao="Secretaria de Fazenda Estadual",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CND Estadual"],
                exigencias_tecnicas=[
                    "Processador Intel Core i7 13ª geração (obrigatório)",
                    "Memória RAM marca Kingston ou Corsair",
                ],
                penalidades=["Multa de 10% por atraso"],
                valor_estimado=Decimal("150000.00"),
            ),
        },
        "expected_risk_level": "high",
        "expected_has_blocking": False,
        "expected_tcu_category": "ESPECIFICACAO_MARCA",
    },
    {
        "id": "eval-002",
        "description": "Certidão sem base legal — risco crítico (HABILITACAO_EXCESSIVA)",
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
        "expected_risk_level": "critical",
        "expected_has_blocking": True,
        "expected_tcu_category": "HABILITACAO_EXCESSIVA",
    },
    {
        "id": "eval-003",
        "description": "Edital padrão limpo — baixo risco",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Aquisição de material de escritório (papel A4, canetas, clips)",
                orgao="Câmara Municipal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "CND Estadual"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("20000.00"),
                garantia_exigida=False,
            ),
        },
        "expected_risk_level": "low",
        "expected_has_blocking": False,
        "expected_tcu_category": None,
    },
    {
        "id": "eval-004",
        "description": "Garantia contratual acima do limite legal — alto risco (GARANTIA_DESPROPORCIONAL)",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Execução de obra de reforma e ampliação predial",
                orgao="Prefeitura Municipal",
                modalidade="concorrencia",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "CND Federal", "Registro CREA/CAU"],
                exigencias_tecnicas=["Responsável técnico com registro CREA ativo"],
                penalidades=["Multa de 10% por atraso", "Rescisão contratual por inadimplência"],
                valor_estimado=Decimal("2000000.00"),
                garantia_exigida=True,
                garantia_percentual=15.0,
                prazo_entrega_dias=180,
            ),
        },
        "expected_risk_level": "high",
        "expected_has_blocking": False,
        "expected_tcu_category": "GARANTIA_DESPROPORCIONAL",
    },
    {
        "id": "eval-005",
        "description": "Exigência financeira desproporcional para ME/EPP — alto risco (RESTRICAO_PORTE)",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento de refeições para servidores",
                orgao="Tribunal Regional Federal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=[
                    "CNPJ ativo",
                    "Balanço patrimonial com patrimônio líquido mínimo de R$ 500.000",
                    "Comprovante de faturamento mínimo de R$ 5.000.000 nos últimos 12 meses",
                ],
                exigencias_tecnicas=[
                    "Empresa com faturamento mínimo anual de R$ 5.000.000",
                ],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("300000.00"),
            ),
        },
        "expected_risk_level": "high",
        "expected_has_blocking": False,
        "expected_tcu_category": "RESTRICAO_PORTE",
    },
]
