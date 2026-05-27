from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Contrato de TI — monitoramento de prazo e marcos",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Desenvolvimento de plataforma de gestão de contratos administrativos",
                orgao="Ministério da Gestão",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 2% por atraso"],
                valor_estimado=Decimal("600000.00"),
                prazo_entrega_dias=180,
                prazo_pagamento_dias=30,
            ),
            "contract_data": (
                "Contrato assinado em 01/01/2024.\n"
                "Vigência: 12 meses (até 31/12/2024).\n"
                "Marco 1: Entrega do módulo de cadastro — 30/03/2024.\n"
                "Marco 2: Entrega do módulo de relatórios — 30/06/2024.\n"
                "Marco 3: Go-live e treinamento — 30/09/2024.\n"
                "Garantia: 5% = R$ 30.000,00 (caução em dinheiro).\n"
                "Pagamento: 30 dias após aceite de cada módulo.\n"
            ),
        },
        "expected_has_alerts": True,
    },
    {
        "id": "eval-002",
        "description": "Contrato de fornecimento — vigência perto do fim",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Fornecimento parcelado de material de limpeza",
                orgao="Hospital Universitário Federal",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "Alvará sanitário"],
                exigencias_tecnicas=[],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("240000.00"),
                prazo_entrega_dias=365,
                prazo_pagamento_dias=30,
            ),
            "contract_data": (
                "Contrato assinado em 01/06/2023.\n"
                "Vigência: 12 meses (vence em 01/06/2024 — VENCIMENTO IMINENTE).\n"
                "Saldo pendente: R$ 20.000,00 em pedidos agendados.\n"
                "Última entrega realizada: 15/05/2024.\n"
                "Nota fiscal pendente: R$ 8.500,00 referente a abril/2024.\n"
            ),
        },
        "expected_has_alerts": True,
    },
    {
        "id": "eval-003",
        "description": "Contrato de serviço em dia — sem alertas pendentes",
        "context": {
            "tender_schema": TenderSchema(
                objeto="Serviços de vigilância e segurança patrimonial",
                orgao="Autarquia Federal de Regulação Elétrica",
                modalidade="pregao_eletronico",
                criterio_julgamento="menor_preco",
                documentos_exigidos=["CNPJ ativo", "Autorização da PF"],
                exigencias_tecnicas=["Vigilantes com curso de formação profissional"],
                penalidades=["Multa de 5% por atraso"],
                valor_estimado=Decimal("480000.00"),
                prazo_entrega_dias=365,
                prazo_pagamento_dias=30,
            ),
            "contract_data": (
                "Contrato assinado em 01/01/2024.\n"
                "Vigência: 24 meses (até 31/12/2025).\n"
                "Status: em execução regular.\n"
                "Último pagamento recebido: abril/2024.\n"
                "Reajuste previsto: janeiro/2025 pelo INPC.\n"
            ),
        },
        "expected_has_alerts": False,
    },
]
