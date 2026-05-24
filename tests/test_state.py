import operator
from datetime import datetime

from src.graph.state import initial_state
from src.schemas.results import AgentError, AuditEvent, HumanApproval


def _err(subgraph: str) -> AgentError:
    return AgentError(
        subgraph=subgraph,
        agent="test",
        error_type="ValueError",
        message="test error",
        timestamp=datetime.utcnow(),
        recoverable=True,
    )


def _event(subgraph: str) -> AuditEvent:
    return AuditEvent(
        subgraph=subgraph,
        agent="test",
        action="test_action",
        input_summary="input",
        output_summary="output",
        model_used="test-model",
        latency_ms=100,
        tokens_used=50,
        timestamp=datetime.utcnow(),
    )


def test_errors_are_append_only():
    state = initial_state("test-001", "raw edital text", "12345678000195")
    err1 = _err("ingestion")
    err2 = _err("validation")

    merged = operator.add(state["errors"], [err1])
    merged = operator.add(merged, [err2])

    assert len(merged) == 2
    assert merged[0].subgraph == "ingestion"
    assert merged[1].subgraph == "validation"


def test_audit_log_is_append_only():
    state = initial_state("test-002", "raw edital text", "12345678000195")
    ev1 = _event("ingestion")
    ev2 = _event("understanding")
    ev3 = _event("validation")

    merged = operator.add(state["audit_log"], [ev1, ev2])
    merged = operator.add(merged, [ev3])

    assert len(merged) == 3
    assert [e.subgraph for e in merged] == ["ingestion", "understanding", "validation"]


def test_human_approvals_are_append_only():
    state = initial_state("test-003", "raw edital text", "12345678000195")
    approval = HumanApproval(
        step="pre_proposal",
        decision="approved",
        comment="Looks good",
        approver="jonatas",
        timestamp=datetime.utcnow(),
    )

    merged = operator.add(state["human_approvals"], [approval])
    assert len(merged) == 1
    assert merged[0].step == "pre_proposal"

    # Segundo append não sobrescreve
    merged2 = operator.add(merged, [approval])
    assert len(merged2) == 2


def test_edital_pages_are_append_only():
    from src.schemas.tender import PageContent

    state = initial_state("test-004", "raw edital text", "12345678000195")
    page1 = PageContent(page_number=1, text="Objeto da licitação", tables=[], is_ocr=False)
    page2 = PageContent(page_number=2, text="Habilitação", tables=[], is_ocr=False)

    merged = operator.add(state["edital_pages"], [page1])
    merged = operator.add(merged, [page2])

    assert len(merged) == 2
    assert merged[0].page_number == 1
    assert merged[1].page_number == 2


def test_initial_state_has_all_fields():
    state = initial_state("test-005", "raw", "12345678000195")

    assert state["edital_id"] == "test-005"
    assert state["current_step"] == "start"
    assert state["tender_schema"] is None
    assert state["errors"] == []
    assert state["audit_log"] == []
    assert state["human_approvals"] == []
    assert state["metrics"] == []
    assert state["edital_pages"] == []
