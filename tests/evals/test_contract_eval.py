"""Eval: ContractAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_contract_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.contract import ContractAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.contract_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_contract_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = ContractAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        has_alerts = len(result.warnings) > 0 or result.human_decision_required
        assert has_alerts == case["expected_has_alerts"], (
            f"Expected has_alerts={case['expected_has_alerts']}, got {has_alerts} "
            f"(warnings={result.warnings}, hitl={result.human_decision_required})"
        )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="contract",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
