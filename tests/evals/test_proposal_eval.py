"""Eval: ProposalAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_proposal_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.proposal import ProposalAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.proposal_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_proposal_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = ProposalAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        if case["expected_has_content"]:
            assert result.content and len(result.content) > 100, (
                f"Expected substantial proposal content, got {len(result.content)} chars"
            )
        if case["expected_has_price"]:
            assert result.price > 0, "Expected price > 0"
            assert result.validity_days > 0, "Expected validity_days > 0"
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="proposal",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
