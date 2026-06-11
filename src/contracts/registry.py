"""Agent contract registry — schema versioning and producer-consumer compatibility."""
from __future__ import annotations

from src.schemas.results import (
    AdvancedPricingResult,
    BidDecision,
    ComplianceResult,
    EligibilityResult,
    ImpugnacaoResult,
    LegalRegimeResult,
)
from src.schemas.tender import TenderSchema

AGENT_CONTRACTS: dict[str, dict] = {
    "compliance": {
        "output_schema": ComplianceResult,
        "version": "2.1.0",
    },
    "eligibility": {
        "output_schema": EligibilityResult,
        "version": "1.0.0",
    },
    "pricing": {
        "output_schema": AdvancedPricingResult,
        "version": "1.4.0",
    },
    "bid_no_bid": {
        "output_schema": BidDecision,
        "version": "1.2.0",
    },
    "impugnacao": {
        "output_schema": ImpugnacaoResult,
        "version": "1.1.0",
    },
    "legal_regime": {
        "output_schema": LegalRegimeResult,
        "version": "1.0.0",
    },
    "tender_understanding": {
        "output_schema": TenderSchema,
        "version": "1.3.0",
    },
}
