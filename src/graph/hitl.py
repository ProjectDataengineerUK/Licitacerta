from __future__ import annotations

from datetime import datetime

from langgraph.types import interrupt

from src.schemas.results import HumanApproval


def hitl_interrupt(state: dict) -> dict:
    """
    Pausa o pipeline antes de ações com risco jurídico.
    Resume somente quando Command(resume=...) chegar via API.
    """
    compliance = state.get("compliance")
    compliance_risk = getattr(compliance, "risk_level", None) if compliance is not None else None

    approval_payload: dict = interrupt(
        {
            "step": "pre_proposal",
            "bid_decision": state.get("bid_decision"),
            "pricing": state.get("pricing"),
            "compliance_risk": compliance_risk,
            "message": "Aprovação necessária antes de gerar proposta.",
        }
    )

    decision = approval_payload.get("decision", "rejected")
    return {
        "human_approvals": [
            HumanApproval(
                step="pre_proposal",
                decision=decision,
                comment=approval_payload.get("comment", ""),
                approver=approval_payload.get("approver", "unknown"),
                timestamp=datetime.utcnow(),
            )
        ],
        "current_step": "approved" if decision == "approved" else "rejected",
    }
