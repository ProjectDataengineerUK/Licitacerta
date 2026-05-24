from __future__ import annotations

from enum import Enum
from typing import Any

from src.config import settings


class ModelTier(str, Enum):
    CLASSIFY = "classify"      # Gemini Flash — classification, routing
    EXTRACT = "extract"        # Gemini Flash — structured extraction from text
    ANALYZE = "analyze"        # Gemini 1.5 Pro — multi-step reasoning
    LEGAL = "legal"            # Claude Sonnet — TCU legal reasoning (compliance only)
    GENERATE = "generate"      # Gemini 2.5 Pro — proposal/contract generation
    GENERATE_PREMIUM = "generate_premium"  # Claude Opus — opt-in premium generation


_LLM_CACHE: dict[str, Any] = {}


def get_llm(tier: ModelTier) -> Any:
    if tier not in _LLM_CACHE:
        _LLM_CACHE[tier] = _build_llm(tier)
    return _LLM_CACHE[tier]


def _build_llm(tier: ModelTier) -> Any:
    if tier == ModelTier.LEGAL:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.model_sonnet, api_key=settings.anthropic_api_key)

    if tier == ModelTier.GENERATE_PREMIUM:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.model_opus, api_key=settings.anthropic_api_key)

    from src.gcp.vertex_ai import VertexAILLM

    model_map = {
        ModelTier.CLASSIFY: settings.gemini_flash,
        ModelTier.EXTRACT: settings.gemini_flash,
        ModelTier.ANALYZE: settings.gemini_pro,
        ModelTier.GENERATE: settings.gemini_generate,
    }
    return VertexAILLM.from_env(model_map[tier])._model


AGENT_TIERS: dict[str, ModelTier] = {
    "read_parse": ModelTier.EXTRACT,
    "tender_understanding": ModelTier.ANALYZE,
    "legal_regime": ModelTier.CLASSIFY,
    "eligibility": ModelTier.CLASSIFY,
    "compliance": ModelTier.LEGAL,
    "blacklist": ModelTier.CLASSIFY,
    "pricing": ModelTier.ANALYZE,
    "bid_no_bid": ModelTier.ANALYZE,
    "watch": ModelTier.CLASSIFY,
    "proposal": ModelTier.GENERATE,
    "contract": ModelTier.ANALYZE,
}
