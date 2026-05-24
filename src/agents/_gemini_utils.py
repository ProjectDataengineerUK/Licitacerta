from __future__ import annotations

from typing import Any


def _extract_usage_gemini(raw_message: Any) -> tuple[int, int]:
    """Extract token counts from Gemini response metadata."""
    try:
        um = raw_message.response_metadata.get("usage_metadata", {})
        return um.get("prompt_token_count", 0), um.get("candidates_token_count", 0)
    except Exception:
        return 0, 0


def _calc_cost_gemini_flash(tokens_in: int, tokens_out: int) -> float:
    """Gemini Flash 2.0: $0.075/M input, $0.30/M output (returns USD)."""
    return (tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000


def _calc_cost_gemini_pro(tokens_in: int, tokens_out: int) -> float:
    """Gemini 1.5 Pro: $1.25/M input, $5.00/M output (context ≤128K; returns USD)."""
    return (tokens_in * 1.25 + tokens_out * 5.00) / 1_000_000


def _calc_cost_gemini_generate(tokens_in: int, tokens_out: int) -> float:
    """Gemini 2.5 Pro Preview: $1.25/M input, $10.00/M output (context ≤200K; returns USD)."""
    return (tokens_in * 1.25 + tokens_out * 10.00) / 1_000_000
