from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from src.schemas.tender import Evidence


class Issue(BaseModel):
    description: str
    severity: Literal["low", "medium", "high", "blocking"]
    evidence: Evidence | None = None


class AgentResult(BaseModel):
    conclusion: str
    confidence: float
    blocking_issues: list[Issue] = []
    warnings: list[str] = []
    evidence: list[Evidence] = []
    human_decision_required: bool = False
    recommended_action: str


class EligibilityResult(AgentResult):
    is_eligible: bool
    missing_documents: list[str] = []
    expiring_certifications: list[str] = []


class ComplianceResult(AgentResult):
    risk_level: Literal["low", "medium", "high", "critical"]
    restrictive_clauses: list[Issue] = []
    tcu_precedents: list[str] = []


class BlacklistResult(BaseModel):
    ceis_blocked: bool
    cnep_blocked: bool
    cepim_blocked: bool
    any_blocked: bool
    checked_at: datetime


class LegalRegimeResult(BaseModel):
    primary_law: str
    modality: str
    special_regime: str | None = None
    confidence: float


class PricingResult(AgentResult):
    cost_estimate: Decimal
    min_margin_pct: float
    recommended_price: Decimal
    scenarios: dict[str, Decimal] = {}


class BidDecision(AgentResult):
    recommendation: Literal[
        "participar",
        "participar_com_ressalvas",
        "pedir_esclarecimento",
        "impugnar",
        "nao_participar",
    ]
    risk_level: Literal["low", "medium", "high"]
    expected_margin_pct: float


class ProposalDraft(BaseModel):
    content: str
    attachments: list[str] = []
    price: Decimal
    validity_days: int
    generated_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None


class HumanApproval(BaseModel):
    step: str
    decision: Literal["approved", "rejected", "modified"]
    comment: str = ""
    approver: str
    timestamp: datetime


class AgentError(BaseModel):
    subgraph: str
    agent: str
    error_type: str
    message: str
    timestamp: datetime
    recoverable: bool


class AuditEvent(BaseModel):
    subgraph: str
    agent: str
    action: str
    input_summary: str
    output_summary: str
    model_used: str
    latency_ms: int
    tokens_used: int
    timestamp: datetime


class AgentMetric(BaseModel):
    subgraph: str
    agent: str
    metric_name: str
    value: float
    timestamp: datetime
