from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.read_parse import ReadParseAgent
from src.config import settings
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def build_ingestion_subgraph():
    agent = ReadParseAgent()

    def run_read_parse(state: TenderState) -> dict:
        t0 = time.time()
        try:
            pages = agent.run({
                "edital_raw": state["edital_raw"],
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "edital_pages": pages,
                "current_step": "ingested",
                "audit_log": [
                    AuditEvent(
                        subgraph="ingestion",
                        agent="read_parse",
                        action="extract_pages",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"pages={len(pages)}",
                        model_used=settings.gemini_flash,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
            }
        except Exception as e:
            return {
                "errors": [
                    AgentError(
                        subgraph="ingestion",
                        agent="read_parse",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "ingestion_failed",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("read_parse", run_read_parse)
    g.set_entry_point("read_parse")
    g.set_finish_point("read_parse")
    return g.compile()
