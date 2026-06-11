import operator
from typing import Annotated, TypedDict

from src.schemas.cashflow import CashflowSimulation
from src.schemas.estrategia import EstrategiaResult
from src.schemas.market import CompetitiveContext
from src.schemas.pregoeiro import PregoeiroPerfil
from src.schemas.results import (
    AgentError,
    AgentMetric,
    AuditEvent,
    BidDecision,
    BlacklistResult,
    ComplianceResult,
    EligibilityResult,
    HumanApproval,
    ImpugnacaoResult,
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
    competitive_context: CompetitiveContext | None
    pricing: PricingResult | None
    bid_decision: BidDecision | None
    impugnacao: ImpugnacaoResult | None

    # --- Simulação (Camada 4b) ---
    cashflow_simulation: CashflowSimulation | None
    estrategia_result: EstrategiaResult | None
    pregoeiro_perfil: PregoeiroPerfil | None

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
        competitive_context=None,
        cashflow_simulation=None,
        estrategia_result=None,
        pregoeiro_perfil=None,
        pricing=None,
        bid_decision=None,
        proposal_draft=None,
        impugnacao=None,
        current_step="start",
        human_approvals=[],
        errors=[],
        audit_log=[],
        metrics=[],
    )
