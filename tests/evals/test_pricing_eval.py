"""Eval: PricingAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_pricing_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.pricing import PricingAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.pricing_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_pricing_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = PricingAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        if case["expected_has_price"]:
            assert result.recommended_price > 0, "Expected recommended_price > 0"
            assert result.cost_estimate > 0, "Expected cost_estimate > 0"
        assert result.min_margin_pct >= case["expected_margin_min"], (
            f"Expected min_margin_pct >= {case['expected_margin_min']}, "
            f"got {result.min_margin_pct}"
        )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="pricing",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
