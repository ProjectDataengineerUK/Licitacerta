"""Eval: LegalRegimeAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_legal_regime_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.legal_regime import LegalRegimeAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.legal_regime_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_legal_regime_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = LegalRegimeAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        assert case["expected_primary_law"] in result.primary_law, (
            f"Expected primary_law to contain {case['expected_primary_law']!r}, "
            f"got {result.primary_law!r}"
        )
        assert result.confidence >= 0.5, f"Expected confidence >= 0.5, got {result.confidence}"
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="legal_regime",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
