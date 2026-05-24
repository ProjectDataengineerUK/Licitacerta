import operator
from typing import Annotated, TypedDict

from src.schemas.results import (
    AgentError,
    AgentMetric,
    AuditEvent,
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    HumanApproval,
    LegalRegimeResult,
    PricingResult,
    ProposalDraft,
)
from src.schemas.tender import PageContent, TenderSchema


class TenderState(TypedDict):
    # --- Entrada ---
    edital_id: str
    edital_raw: str
    company_cnpj: str

    # --- Ingestão (Camada 1) ---
    edital_pages: Annotated[list[PageContent], operator.add]

    # --- Entendimento (Camada 2) ---
    tender_schema: TenderSchema | None
    legal_regime: LegalRegimeResult | None

    # --- Validação (Camada 3) ---
    eligibility: EligibilityResult | None
    compliance: ComplianceResult | None
    blacklist: BlacklistResult | None

    # --- Decisão (Camada 4) ---
    pricing: PricingResult | None
    bid_decision: BidDecision | None

    # --- Execução (Camada 5) ---
    proposal_draft: ProposalDraft | None

    # --- Controle de fluxo ---
    current_step: str

    # --- Append-only (reducers) ---
    human_approvals: Annotated[list[HumanApproval], operator.add]
    errors: Annotated[list[AgentError], operator.add]
    audit_log: Annotated[list[AuditEvent], operator.add]
    metrics: Annotated[list[AgentMetric], operator.add]


def initial_state(edital_id: str, edital_raw: str, company_cnpj: str) -> TenderState:
    return TenderState(
        edital_id=edital_id,
        edital_raw=edital_raw,
        company_cnpj=company_cnpj,
        edital_pages=[],
        tender_schema=None,
        legal_regime=None,
        eligibility=None,
        compliance=None,
        blacklist=None,
        pricing=None,
        bid_decision=None,
        proposal_draft=None,
        current_step="start",
        human_approvals=[],
        errors=[],
        audit_log=[],
        metrics=[],
    )
