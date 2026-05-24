from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.hitl import hitl_interrupt
from src.graph.state import TenderState

ROUTING: dict[str, str] = {
    "start": "subgraph_ingestion",
    "ingested": "subgraph_understanding",
    "understood": "subgraph_validation",
    "validated": "subgraph_decision",
    "decided": "interrupt_before_execution",
    "approved": "subgraph_execution",
    "executed": "subgraph_post_award",
    "completed": END,
    # Error/terminal states
    "ingestion_failed": END,
    "understanding_failed": END,
    "execution_failed": END,
    "rejected": END,
}


def _route(state: TenderState) -> str:
    return ROUTING.get(state["current_step"], END)


def _placeholder(name: str):
    def node(state: TenderState) -> dict:
        return {"current_step": f"{name}_not_implemented"}

    node.__name__ = name
    return node


def build_supervisor(
    ingestion_graph=None,
    understanding_graph=None,
    validation_graph=None,
    decision_graph=None,
    execution_graph=None,
    post_award_graph=None,
    checkpointer=None,
):
    from src.graph.subgraphs.decision import build_decision_subgraph
    from src.graph.subgraphs.execution import build_execution_subgraph
    from src.graph.subgraphs.ingestion import build_ingestion_subgraph
    from src.graph.subgraphs.post_award import build_post_award_subgraph
    from src.graph.subgraphs.understanding import build_understanding_subgraph
    from src.graph.subgraphs.validation import build_validation_subgraph

    ing = ingestion_graph or build_ingestion_subgraph()
    ung = understanding_graph or build_understanding_subgraph()
    val = validation_graph or build_validation_subgraph()
    dec = decision_graph or build_decision_subgraph()
    exc = execution_graph or build_execution_subgraph()
    pos = post_award_graph or build_post_award_subgraph()

    g: StateGraph = StateGraph(TenderState)
    g.add_node("subgraph_ingestion", ing)
    g.add_node("subgraph_understanding", ung)
    g.add_node("subgraph_validation", val)
    g.add_node("subgraph_decision", dec)
    g.add_node("interrupt_before_execution", hitl_interrupt)
    g.add_node("subgraph_execution", exc)
    g.add_node("subgraph_post_award", pos)

    g.set_entry_point("subgraph_ingestion")

    for node_name in (
        "subgraph_ingestion",
        "subgraph_understanding",
        "subgraph_validation",
        "subgraph_decision",
        "interrupt_before_execution",
        "subgraph_execution",
        "subgraph_post_award",
    ):
        g.add_conditional_edges(node_name, _route)

    return g.compile(checkpointer=checkpointer)
