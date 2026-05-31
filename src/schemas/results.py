from datetime import date, datetime
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
    juridical_context_used: bool = False


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


class ImpostoResult(BaseModel):
    regime: str
    aliquota_total_pct: float
    valor_impostos_brl: Decimal
    detalhamento: dict[str, Decimal] = {}


class BDIResult(BaseModel):
    bdi_pct: float
    valor_bdi_brl: Decimal | None = None
    composicao: dict[str, float] = {}


class CapitalGiroResult(BaseModel):
    capital_necessario_brl: Decimal
    alerta: Literal["ok", "warning", "critical"] = "ok"
    limite_credito_brl: Decimal | None = None


class CenarioPrecificacao(BaseModel):
    nome: str
    valor_proposta_brl: Decimal
    margem_bruta_pct: float
    margem_liquida_pct: float
    margem_liquida_brl: Decimal
    capital_necessario_brl: Decimal
    viavel: bool


class AdvancedPricingResult(PricingResult):
    impostos: ImpostoResult | None = None
    bdi: BDIResult | None = None
    capital_giro: CapitalGiroResult | None = None
    cenarios: list[CenarioPrecificacao] = []
    margem_liquida_brl: Decimal | None = None
    margem_liquida_pct: float | None = None


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


class ImpugnacaoAction(BaseModel):
    tipo: Literal["impugnar", "pedir_esclarecimento"]
    clause_description: str
    fundamento_legal: str
    minuta: str
    prazo_limite: date | None = None
    valido: bool = True


class ImpugnacaoResult(AgentResult):
    recommendation: Literal["participar", "pedir_esclarecimento", "impugnar", "nao_participar"]
    actions: list[ImpugnacaoAction] = []
    risk_after_impugnacao: str | None = None
    prazo_limite: date | None = None


class AgentMetric(BaseModel):
    subgraph: str
    agent: str
    metric_name: str
    value: float
    timestamp: datetime
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_brl: float | None = None
    latency_ms: int | None = None
    model_id: str | None = None
