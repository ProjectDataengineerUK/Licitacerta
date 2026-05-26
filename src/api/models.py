from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    edital_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    edital_raw: str
    cnpj: str


class ApproveRequest(BaseModel):
    approver: str
    comment: str = ""


class RejectRequest(BaseModel):
    approver: str
    reason: str


class RunStatus(BaseModel):
    run_id: str
    current_step: str
    edital_id: str
    bid_decision: dict | None = None
    pricing: dict | None = None
    errors: list[dict] = []


class RunResult(RunStatus):
    tender_schema: dict | None = None
    eligibility: dict | None = None
    compliance: dict | None = None
    blacklist: dict | None = None
    proposal_draft: dict | None = None
    audit_log: list[dict] = []


class AgentCost(BaseModel):
    name: str
    tokens_in: int
    tokens_out: int
    cost_brl: float
    latency_ms: int | None = None


class RunCost(BaseModel):
    run_id: str
    agents: list[AgentCost]
    total_cost_brl: float
    source: Literal["bigquery", "memory"]


def _serialize(obj) -> dict | None:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return dict(obj)
