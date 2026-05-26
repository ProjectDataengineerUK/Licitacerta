from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.contract import ContractAgent
from src.config import settings
from src.graph._async_utils import run_in_thread
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def build_post_award_subgraph():
    _contract: ContractAgent | None = None

    async def run_contract(state: TenderState) -> dict:
        nonlocal _contract
        if _contract is None:
            _contract = ContractAgent()
        t0 = time.time()
        try:
            result = await run_in_thread(_contract.run, {
                "tender_schema": state.get("tender_schema"),
                "proposal_draft": state.get("proposal_draft"),
                "contract_data": {},
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            metric = _contract.get_last_metric()
            return {
                "current_step": "completed",
                "audit_log": [
                    AuditEvent(
                        subgraph="post_award",
                        agent="contract",
                        action="monitor_contract",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"status={result.contract_status} obligations={len(result.obligations)}",
                        model_used=settings.gemini_pro,
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
                        subgraph="post_award",
                        agent="contract",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "completed",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("contract", run_contract)
    g.set_entry_point("contract")
    g.set_finish_point("contract")
    return g.compile()
