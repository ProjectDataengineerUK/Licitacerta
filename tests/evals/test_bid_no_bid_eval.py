"""Eval: BidNoBidAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_bid_no_bid_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.bid_no_bid import BidNoBidAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.bid_no_bid_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_bid_no_bid_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = BidNoBidAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        assert result.recommendation in case["expected_recommendation_in"], (
            f"Expected recommendation in {case['expected_recommendation_in']}, "
            f"got {result.recommendation!r}"
        )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="bid_no_bid",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
