

from src.graph.state import TenderState, initial_state
from src.graph.supervisor import ROUTING, _route


def _state_with_step(step: str) -> TenderState:
    s = initial_state("test-sup", "raw", "12345678000195")
    s["current_step"] = step
    return s


def test_routing_from_start():
    assert _route(_state_with_step("start")) == "subgraph_ingestion"


def test_routing_from_ingested():
    assert _route(_state_with_step("ingested")) == "subgraph_understanding"


def test_routing_from_understood():
    assert _route(_state_with_step("understood")) == "subgraph_validation"


def test_routing_from_validated():
    assert _route(_state_with_step("validated")) == "subgraph_decision"


def test_routing_from_decided():
    assert _route(_state_with_step("decided")) == "interrupt_before_execution"


def test_routing_from_approved():
    assert _route(_state_with_step("approved")) == "subgraph_execution"


def test_routing_from_executed():
    assert _route(_state_with_step("executed")) == "subgraph_post_award"


def test_routing_terminal_states_end():
    from langgraph.graph import END

    for step in ("completed", "ingestion_failed", "understanding_failed", "execution_failed", "rejected"):
        assert _route(_state_with_step(step)) == END, f"Step '{step}' should route to END"


def test_routing_unknown_step_ends():
    from langgraph.graph import END

    assert _route(_state_with_step("nonexistent_step")) == END


def test_all_routing_keys_covered():
    expected_steps = {
        "start", "ingested", "understood", "validated", "decided",
        "approved", "executed", "completed",
        "ingestion_failed", "understanding_failed", "execution_failed", "rejected",
    }
    assert expected_steps == set(ROUTING.keys())
