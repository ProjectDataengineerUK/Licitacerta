from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.proposal import ProposalAgent
from src.config import settings
from src.graph._async_utils import run_in_thread
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def build_execution_subgraph():
    _proposal: ProposalAgent | None = None

    async def run_proposal(state: TenderState) -> dict:
        nonlocal _proposal
        if _proposal is None:
            _proposal = ProposalAgent()
        t0 = time.time()
        try:
            result = await run_in_thread(_proposal.run, {
                "tender_schema": state.get("tender_schema"),
                "pricing": state.get("pricing"),
                "bid_decision": state.get("bid_decision"),
                "human_approvals": state.get("human_approvals", []),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            metric = _proposal.get_last_metric()
            return {
                "proposal_draft": result,
                "current_step": "executed",
                "audit_log": [
                    AuditEvent(
                        subgraph="execution",
                        agent="proposal",
                        action="generate_proposal",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"price={result.price} validity={result.validity_days}d",
                        model_used=settings.gemini_generate,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "errors": [
                    AgentError(
                        subgraph="execution",
                        agent="proposal",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=False,
                    )
                ],
                "current_step": "execution_failed",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("proposal", run_proposal)
    g.set_entry_point("proposal")
    g.set_finish_point("proposal")
    return g.compile()
