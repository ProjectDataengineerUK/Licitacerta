from __future__ import annotations

from decimal import Decimal

from src.schemas.tender import TenderSchema

_TENDER = TenderSchema(
    objeto="Fornecimento de equipamentos de TI",
    orgao="Secretaria de Saúde Estadual",
    modalidade="pregao_eletronico",
    criterio_julgamento="menor_preco",
    documentos_exigidos=["CNPJ ativo", "CND Federal"],
    exigencias_tecnicas=[],
    penalidades=["Multa de 2% por atraso"],
    valor_estimado=Decimal("500000.00"),
)

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Monitoramento de prazo iminente — deve gerar alerta urgente",
        "context": {
            "tender_schema": _TENDER,
            "monitoring_data": (
                "Data de abertura das propostas: amanhã às 09:00.\n"
                "Status: aguardando proposta final.\n"
                "Última atualização do portal: hoje às 15:30.\n"
                "Impugnações recebidas: nenhuma.\n"
            ),
        },
        "expected_has_alerts": True,
        "expected_urgency": "high",
    },
    {
        "id": "eval-002",
        "description": "Monitoramento normal — prazo em 15 dias sem eventos críticos",
        "context": {
            "tender_schema": _TENDER,
            "monitoring_data": (
                "Data de abertura: 15 dias.\n"
                "Status: publicado, recebendo propostas.\n"
                "Impugnações: nenhuma.\n"
                "Errata: nenhuma.\n"
            ),
        },
        "expected_has_alerts": False,
        "expected_urgency": "low",
    },
    {
        "id": "eval-003",
        "description": "Errata publicada — deve gerar alerta sobre mudança de prazo",
        "context": {
            "tender_schema": _TENDER,
            "monitoring_data": (
                "ERRATA Nº 001: Fica adiada a sessão pública para o dia 30/06/2024 às 10:00.\n"
                "Motivo: impugnação parcialmente acatada — revisão de cláusula de habilitação técnica.\n"
                "Nova data limite para propostas: 29/06/2024.\n"
            ),
        },
        "expected_has_alerts": True,
        "expected_urgency": "medium",
    },
    {
        "id": "eval-004",
        "description": "Pregão suspenso por decisão judicial — alerta crítico",
        "context": {
            "tender_schema": _TENDER,
            "monitoring_data": (
                "AVISO: Pregão suspenso por liminar judicial proferida pelo Tribunal de Contas.\n"
                "Processo TC-012345/2024.\n"
                "Previsão de retomada: indeterminada.\n"
                "Recomendação: aguardar decisão de mérito.\n"
            ),
        },
        "expected_has_alerts": True,
        "expected_urgency": "high",
    },
]
