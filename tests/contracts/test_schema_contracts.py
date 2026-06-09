"""Schema contract tests — detect breaking changes before merge (AT-005)."""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime

import pytest

from src.schemas.results import (
    AdvancedPricingResult,
    BidDecision,
    ComplianceResult,
    EligibilityResult,
    ImpugnacaoResult,
)
from src.contracts.registry import AGENT_CONTRACTS


def _make_compliance() -> ComplianceResult:
    return ComplianceResult(
        conclusion="Edital dentro dos padrões legais",
        confidence=0.9,
        recommended_action="Participar",
        risk_level="low",
    )


def _make_pricing() -> AdvancedPricingResult:
    return AdvancedPricingResult(
        conclusion="Margem viável",
        confidence=0.85,
        recommended_action="Participar com preço R$120k",
        cost_estimate=Decimal("100000"),
        min_margin_pct=15.0,
        recommended_price=Decimal("120000"),
    )


def _make_bid() -> BidDecision:
    return BidDecision(
        conclusion="Recomendado participar",
        confidence=0.88,
        recommended_action="Submeter proposta",
        recommendation="participar",
        risk_level="low",
        expected_margin_pct=15.0,
    )


# ── Contract: all registered agents have output_schema ───────────────────────
def test_all_contracts_have_output_schema():
    for agent, contract in AGENT_CONTRACTS.items():
        assert "output_schema" in contract, f"{agent}: missing output_schema"
        assert "version" in contract, f"{agent}: missing version"


# ── AT-005: compliance output serializável/deserializável ────────────────────
def test_compliance_round_trip():
    obj = _make_compliance()
    data = obj.model_dump()
    restored = ComplianceResult.model_validate(data)
    assert restored.risk_level == obj.risk_level
    assert restored.confidence == obj.confidence


def test_pricing_round_trip():
    obj = _make_pricing()
    data = obj.model_dump()
    restored = AdvancedPricingResult.model_validate(data)
    assert restored.recommended_price == obj.recommended_price


def test_bid_decision_round_trip():
    obj = _make_bid()
    data = obj.model_dump()
    restored = BidDecision.model_validate(data)
    assert restored.recommendation == obj.recommendation


# ── ComplianceResult é compatível como entrada do BidNoBidAgent ─────────────
def test_compliance_compatible_with_bid_no_bid_context():
    compliance = _make_compliance()
    # BidNoBidAgent expects dict with compliance key
    context = {
        "compliance": compliance,
        "eligibility": None,
        "pricing": None,
        "blacklist": None,
        "tender_schema": None,
        "run_id": "test",
        "tenant_id": "test",
    }
    # If compliance is accessible and has expected fields, no breaking change
    assert hasattr(compliance, "risk_level")
    assert hasattr(compliance, "blocking_issues")
    assert hasattr(compliance, "tcu_precedents")


# ── EligibilityResult não perdeu campos críticos ─────────────────────────────
def test_eligibility_required_fields():
    e = EligibilityResult(
        conclusion="Elegível",
        confidence=0.95,
        recommended_action="Participar",
        is_eligible=True,
    )
    assert e.missing_documents == []
    assert e.expiring_certifications == []


# ── supply_chain field added to ComplianceResult without breaking existing ───
def test_compliance_supply_chain_optional():
    obj = ComplianceResult(
        conclusion="OK",
        confidence=0.9,
        recommended_action="Participar",
        risk_level="low",
    )
    assert obj.supply_chain is None  # optional, must default to None
