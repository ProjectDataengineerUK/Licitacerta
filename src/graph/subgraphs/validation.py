from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.compliance import ComplianceAgent
from src.agents.eligibility import EligibilityAgent
from src.config import settings
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent, BlacklistResult


def build_validation_subgraph(blacklist_fn=None):
    """
    blacklist_fn: callable(cnpj, api_key) → BlacklistResult
    Injetável para testes sem chamada HTTP real.
    """
    from src.config import settings as cfg
    from src.tools.blacklist import check_blacklist

    _blacklist = blacklist_fn or (lambda cnpj: check_blacklist(cnpj, cfg.cgu_api_key))
    _elig: EligibilityAgent | None = None
    _comp: ComplianceAgent | None = None

    def run_eligibility(state: TenderState) -> dict:
        nonlocal _elig
        if _elig is None:
            _elig = EligibilityAgent()
        t0 = time.time()
        try:
            result = _elig.run({
                "tender_schema": state.get("tender_schema"),
                "company_cnpj": state["company_cnpj"],
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "eligibility": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="validation",
                        agent="eligibility",
                        action="check_eligibility",
                        input_summary=f"cnpj={state['company_cnpj']}",
                        output_summary=f"eligible={result.is_eligible} issues={len(result.blocking_issues)}",
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
                        subgraph="validation",
                        agent="eligibility",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    def run_compliance(state: TenderState) -> dict:
        nonlocal _comp
        if _comp is None:
            _comp = ComplianceAgent()
        t0 = time.time()
        try:
            result = _comp.run({
                "tender_schema": state.get("tender_schema"),
                "legal_regime": state.get("legal_regime"),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "compliance": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="validation",
                        agent="compliance",
                        action="check_compliance",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"risk={result.risk_level} clauses={len(result.restrictive_clauses)}",
                        model_used=settings.model_sonnet,
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
                        subgraph="validation",
                        agent="compliance",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    def run_blacklist(state: TenderState) -> dict:
        t0 = time.time()
        try:
            result: BlacklistResult = _blacklist(state["company_cnpj"])
            return {
                "blacklist": result,
                "current_step": "validated",
                "audit_log": [
                    AuditEvent(
                        subgraph="validation",
                        agent="blacklist",
                        action="check_blacklist",
                        input_summary=f"cnpj={state['company_cnpj']}",
                        output_summary=f"blocked={result.any_blocked}",
                        model_used="deterministic",
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
                        subgraph="validation",
                        agent="blacklist",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "validated",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("eligibility", run_eligibility)
    g.add_node("compliance", run_compliance)
    g.add_node("blacklist", run_blacklist)

    g.set_entry_point("eligibility")
    g.add_edge("eligibility", "compliance")
    g.add_edge("compliance", "blacklist")
    g.set_finish_point("blacklist")
    return g.compile()
