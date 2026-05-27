"""Eval: EligibilityAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_eligibility_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.eligibility import EligibilityAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.eligibility_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_eligibility_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = EligibilityAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        assert result.is_eligible == case["expected_is_eligible"], (
            f"Expected is_eligible={case['expected_is_eligible']}, got {result.is_eligible}"
        )
        has_blocking = len(result.blocking_issues) > 0
        assert has_blocking == case["expected_has_blocking"], (
            f"Expected has_blocking={case['expected_has_blocking']}, got {has_blocking}"
        )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="eligibility",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
