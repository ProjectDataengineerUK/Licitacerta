from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.legal_regime import LegalRegimeAgent
from src.agents.tender_understanding import TenderUnderstandingAgent
from src.config import settings
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def build_understanding_subgraph():
    _tu: TenderUnderstandingAgent | None = None
    _lr: LegalRegimeAgent | None = None

    def run_tender_understanding(state: TenderState) -> dict:
        nonlocal _tu
        if _tu is None:
            _tu = TenderUnderstandingAgent()
        t0 = time.time()
        try:
            pages_text = "\n\n".join(
                f"[Página {p.page_number}]\n{p.text}" for p in state["edital_pages"]
            )
            schema = _tu.run({
                "edital_pages": pages_text,
                "edital_id": state["edital_id"],
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "tender_schema": schema,
                "audit_log": [
                    AuditEvent(
                        subgraph="understanding",
                        agent="tender_understanding",
                        action="extract_schema",
                        input_summary=f"pages={len(state['edital_pages'])}",
                        output_summary=f"objeto={schema.objeto[:60]}",
                        model_used=settings.gemini_pro,
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
                        subgraph="understanding",
                        agent="tender_understanding",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "understanding_failed",
            }

    def run_legal_regime(state: TenderState) -> dict:
        nonlocal _lr
        if state.get("current_step") == "understanding_failed":
            return {}
        if _lr is None:
            _lr = LegalRegimeAgent()
        t0 = time.time()
        try:
            pages_text = "\n\n".join(
                f"[Página {p.page_number}]\n{p.text}" for p in state["edital_pages"]
            )
            regime = _lr.run({
                "edital_pages": pages_text,
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "legal_regime": regime,
                "current_step": "understood",
                "audit_log": [
                    AuditEvent(
                        subgraph="understanding",
                        agent="legal_regime",
                        action="classify_regime",
                        input_summary=f"pages={len(state['edital_pages'])}",
                        output_summary=f"law={regime.primary_law} confidence={regime.confidence:.2f}",
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
                        subgraph="understanding",
                        agent="legal_regime",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "understanding_failed",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("tender_understanding", run_tender_understanding)
    g.add_node("legal_regime", run_legal_regime)
    g.set_entry_point("tender_understanding")
    g.add_edge("tender_understanding", "legal_regime")
    g.set_finish_point("legal_regime")
    return g.compile()
