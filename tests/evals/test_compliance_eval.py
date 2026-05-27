"""Eval: ComplianceAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_compliance_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.compliance import ComplianceAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.compliance_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_compliance_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = ComplianceAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        assert result.risk_level == case["expected_risk_level"], (
            f"Expected risk_level={case['expected_risk_level']!r}, got {result.risk_level!r}"
        )
        has_blocking = len(result.blocking_issues) > 0
        assert has_blocking == case["expected_has_blocking"], (
            f"Expected has_blocking={case['expected_has_blocking']}, "
            f"got {has_blocking} (issues: {result.blocking_issues})"
        )
        if case.get("expected_tcu_category"):
            clauses_text = str(result.restrictive_clauses)
            assert case["expected_tcu_category"] in clauses_text or any(
                case["expected_tcu_category"] in p for p in result.tcu_precedents
            ), f"Expected TCU category {case['expected_tcu_category']!r} not found in result"
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="compliance",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
