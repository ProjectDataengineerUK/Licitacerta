"""Unit tests for model_router — no real LLM calls."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.agents.model_router import AGENT_TIERS, ModelTier


def test_all_12_agents_have_tiers():
    expected = {
        "read_parse", "tender_understanding", "legal_regime", "eligibility",
        "compliance", "blacklist", "pricing", "bid_no_bid", "watch",
        "proposal", "contract",
    }
    assert set(AGENT_TIERS.keys()) == expected


def test_compliance_uses_legal_tier():
    assert AGENT_TIERS["compliance"] == ModelTier.LEGAL


def test_proposal_uses_generate_tier():
    assert AGENT_TIERS["proposal"] == ModelTier.GENERATE


def test_eligibility_uses_classify_tier():
    assert AGENT_TIERS["eligibility"] == ModelTier.CLASSIFY


@patch("src.gcp.vertex_ai.VertexAILLM.from_env")
def test_get_llm_gemini_tiers(mock_from_env):
    from src.agents import model_router as mr
    mr._LLM_CACHE.clear()

    mock_llm = MagicMock()
    mock_llm._model = MagicMock()
    mock_from_env.return_value = mock_llm

    for tier in [ModelTier.CLASSIFY, ModelTier.EXTRACT, ModelTier.ANALYZE, ModelTier.GENERATE]:
        mr.get_llm(tier)

    assert mock_from_env.call_count == 4
    mr._LLM_CACHE.clear()


@patch("langchain_anthropic.ChatAnthropic")
def test_get_llm_legal_uses_anthropic(mock_anthropic_cls):
    from src.agents import model_router as mr
    mr._LLM_CACHE.clear()
    mock_anthropic_cls.return_value = MagicMock()
    mr.get_llm(ModelTier.LEGAL)
    mr._LLM_CACHE.clear()


@patch("langchain_anthropic.ChatAnthropic")
def test_get_llm_premium_uses_opus(mock_anthropic_cls):
    from src.agents import model_router as mr
    mr._LLM_CACHE.clear()
    mock_anthropic_cls.return_value = MagicMock()
    mr.get_llm(ModelTier.GENERATE_PREMIUM)
    mr._LLM_CACHE.clear()
