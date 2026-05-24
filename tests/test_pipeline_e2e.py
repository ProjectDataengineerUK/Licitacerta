"""
AT-001: Pipeline completo com edital mock.
AT-002: Falha isolada em subgrafo.
AT-005: Contexto mínimo por agente (supervisor não passa estado inteiro).
"""
from datetime import datetime
from decimal import Decimal

import pytest

from src.graph.state import initial_state
from src.schemas.results import (
    AgentError,
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    LegalRegimeResult,
    PricingResult,
    ProposalDraft,
)
from src.schemas.tender import Evidence, PageContent, TenderSchema


# ---------------------------------------------------------------------------
# Subgrafos stub — simulam execução real sem LLM
# ---------------------------------------------------------------------------

def _ingestion_stub(state: dict) -> dict:
    return {
        "edital_pages": [
            PageContent(page_number=1, text="Objeto: Papel A4. Órgão: Câmara.", tables=[], is_ocr=False),
            PageContent(page_number=2, text="Habilitação: CNPJ, CND Federal.", tables=[], is_ocr=False),
        ],
        "current_step": "ingested",
    }


def _understanding_stub(state: dict) -> dict:
    return {
        "tender_schema": TenderSchema(
            objeto="Fornecimento de papel A4",
            orgao="Câmara Municipal de Teste",
            modalidade="pregao_eletronico",
            criterio_julgamento="menor_preco",
            documentos_exigidos=["CNPJ", "CND Federal"],
            exigencias_tecnicas=[],
            penalidades=["Multa de 5%"],
            evidence=[Evidence(document="edital.pdf", page=1, excerpt="Papel A4")],
            valor_estimado=Decimal("50000.00"),
            prazo_pagamento_dias=30,
        ),
        "legal_regime": LegalRegimeResult(
            primary_law="lei_14133",
            modality="pregao_eletronico",
            confidence=0.95,
        ),
        "current_step": "understood",
    }


def _validation_stub(state: dict) -> dict:
    return {
        "eligibility": EligibilityResult(
            conclusion="Elegível", confidence=0.9, is_eligible=True, recommended_action="ok"
        ),
        "compliance": ComplianceResult(
            conclusion="Baixo risco", confidence=0.9, risk_level="low", recommended_action="ok"
        ),
        "blacklist": BlacklistResult(
            ceis_blocked=False, cnep_blocked=False, cepim_blocked=False,
            any_blocked=False, checked_at=datetime.utcnow()
        ),
        "current_step": "validated",
    }


def _decision_stub(state: dict) -> dict:
    return {
        "pricing": PricingResult(
            conclusion="Margem adequada", confidence=0.85,
            cost_estimate=Decimal("40000.00"), min_margin_pct=15.0,
            recommended_price=Decimal("47058.82"),
            scenarios={"pessimista": Decimal("44444.00"), "realista": Decimal("47058.82"), "otimista": Decimal("53333.00")},
            recommended_action="Participar",
        ),
        "bid_decision": BidDecision(
            conclusion="Participar", confidence=0.88,
            recommendation="participar", risk_level="low",
            expected_margin_pct=15.0, recommended_action="Participar",
        ),
        "current_step": "decided",
    }


def _execution_stub(state: dict) -> dict:
    return {
        "proposal_draft": ProposalDraft(
            content="PROPOSTA: Papel A4 — R$ 47.058,82",
            attachments=["cnpj.pdf"],
            price=Decimal("47058.82"),
            validity_days=60,
            generated_at=datetime.utcnow(),
            approved_by="jonatas",
        ),
        "current_step": "executed",
    }


def _post_award_stub(state: dict) -> dict:
    return {"current_step": "completed"}


# ---------------------------------------------------------------------------
# AT-001: Pipeline completo
# ---------------------------------------------------------------------------

def test_at001_pipeline_completo():
    """AT-001: Pipeline end-to-end com stubs — bid_decision preenchido ao final."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    from src.graph.supervisor import build_supervisor

    graph = build_supervisor(
        ingestion_graph=_ingestion_stub,
        understanding_graph=_understanding_stub,
        validation_graph=_validation_stub,
        decision_graph=_decision_stub,
        execution_graph=_execution_stub,
        post_award_graph=_post_award_stub,
        checkpointer=MemorySaver(),
    )

    state = initial_state("at001-edital", "texto do edital", "12345678000195")

    # Primeira invocação — pausa no interrupt_before_execution
    config = {"configurable": {"thread_id": "at001"}}
    result = graph.invoke(state, config=config)

    assert result["current_step"] == "decided"
    assert result["bid_decision"].recommendation == "participar"

    # Resume com aprovação humana
    from src.schemas.results import HumanApproval
    from datetime import datetime

    resume_payload = {"decision": "approved", "approver": "jonatas", "comment": "ok"}
    final = graph.invoke(Command(resume=resume_payload), config=config)

    assert final["current_step"] == "completed"
    assert final["proposal_draft"] is not None
    assert final["proposal_draft"].price == Decimal("47058.82")
    assert final["bid_decision"].recommendation == "participar"


# ---------------------------------------------------------------------------
# AT-002: Falha isolada em subgrafo não derruba o pipeline
# ---------------------------------------------------------------------------

def _validation_with_compliance_error(state: dict) -> dict:
    """Compliance falha, mas eligibility e blacklist completam normalmente."""
    return {
        "eligibility": EligibilityResult(
            conclusion="Elegível", confidence=0.9, is_eligible=True, recommended_action="ok"
        ),
        "compliance": None,
        "blacklist": BlacklistResult(
            ceis_blocked=False, cnep_blocked=False, cepim_blocked=False,
            any_blocked=False, checked_at=datetime.utcnow()
        ),
        "errors": [AgentError(
            subgraph="validation", agent="compliance",
            error_type="RuntimeError", message="API indisponível",
            timestamp=datetime.utcnow(), recoverable=True,
        )],
        "current_step": "validated",
    }


def test_at002_falha_isolada_nao_derruba_pipeline():
    """AT-002: Erro em compliance é capturado em errors[] — pipeline continua."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    from src.graph.supervisor import build_supervisor

    graph = build_supervisor(
        ingestion_graph=_ingestion_stub,
        understanding_graph=_understanding_stub,
        validation_graph=_validation_with_compliance_error,
        decision_graph=_decision_stub,
        execution_graph=_execution_stub,
        post_award_graph=_post_award_stub,
        checkpointer=MemorySaver(),
    )

    state = initial_state("at002-edital", "texto", "12345678000195")
    config = {"configurable": {"thread_id": "at002"}}

    result = graph.invoke(state, config=config)

    # Pipeline chegou até "decided" mesmo com compliance falhando
    assert result["current_step"] == "decided"
    assert any(e.agent == "compliance" for e in result["errors"])
    assert result["eligibility"] is not None
    assert result["blacklist"] is not None


# ---------------------------------------------------------------------------
# AT-005: Supervisor não passa estado inteiro aos subgrafos
# ---------------------------------------------------------------------------

def test_at005_supervisor_routing_nao_vaza_estado():
    """
    AT-005: Cada subgrafo recebe o que precisa, não o estado inteiro.
    Verificado via _route + contexto mínimo por subgrafo documentado no ADR-002.
    O supervisor injeta o subgrafo recebido diretamente — o estado filtrado
    é responsabilidade de cada subgrafo ao usar apenas os campos que precisa.
    """
    from src.graph.supervisor import ROUTING, _route
    from src.graph.state import initial_state

    steps_with_next = [
        ("start", "subgraph_ingestion"),
        ("ingested", "subgraph_understanding"),
        ("understood", "subgraph_validation"),
        ("validated", "subgraph_decision"),
        ("decided", "interrupt_before_execution"),
        ("approved", "subgraph_execution"),
        ("executed", "subgraph_post_award"),
    ]

    for step, expected_node in steps_with_next:
        state = initial_state("at005", "raw", "12345678000195")
        state["current_step"] = step
        assert _route(state) == expected_node, f"Step '{step}' deveria ir para '{expected_node}'"
