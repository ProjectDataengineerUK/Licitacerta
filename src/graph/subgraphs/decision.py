from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import StateGraph

from src.agents.bid_no_bid import BidNoBidAgent
from src.agents.pricing import PricingAgent
from src.config import settings
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def build_decision_subgraph():
    _pricing: PricingAgent | None = None
    _bid: BidNoBidAgent | None = None

    def run_pricing(state: TenderState) -> dict:
        nonlocal _pricing
        if _pricing is None:
            _pricing = PricingAgent()
        t0 = time.time()
        try:
            result = _pricing.run({
                "tender_schema": state.get("tender_schema"),
                "eligibility": state.get("eligibility"),
                "compliance": state.get("compliance"),
                "blacklist": state.get("blacklist"),
                "company_cnpj": state["company_cnpj"],
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "pricing": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="pricing",
                        action="calculate_price",
                        input_summary=f"cnpj={state['company_cnpj']}",
                        output_summary=f"price={result.recommended_price} margin={result.min_margin_pct:.1f}%",
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
                        subgraph="decision",
                        agent="pricing",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    def run_bid_no_bid(state: TenderState) -> dict:
        nonlocal _bid
        if _bid is None:
            _bid = BidNoBidAgent()
        t0 = time.time()
        try:
            result = _bid.run({
                "tender_schema": state.get("tender_schema"),
                "eligibility": state.get("eligibility"),
                "compliance": state.get("compliance"),
                "blacklist": state.get("blacklist"),
                "pricing": state.get("pricing"),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            return {
                "bid_decision": result,
                "current_step": "decided",
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="bid_no_bid",
                        action="decide",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"recommendation={result.recommendation} risk={result.risk_level}",
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
                        subgraph="decision",
                        agent="bid_no_bid",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "decided",
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("price_calc", run_pricing)
    g.add_node("bid_no_bid", run_bid_no_bid)
    g.set_entry_point("price_calc")
    g.add_edge("price_calc", "bid_no_bid")
    g.set_finish_point("bid_no_bid")
    return g.compile()
