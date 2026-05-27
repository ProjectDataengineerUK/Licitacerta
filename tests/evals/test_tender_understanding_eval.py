"""Eval: TenderUnderstandingAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_tender_understanding_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.tender_understanding import TenderUnderstandingAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.tender_understanding_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_tender_understanding_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = TenderUnderstandingAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        result = agent.run(case["context"])
        result_dict = result.model_dump()

        assert result.modalidade == case["expected_modalidade"], (
            f"Expected modalidade={case['expected_modalidade']!r}, got {result.modalidade!r}"
        )
        if case["expected_has_valor"]:
            assert result.valor_estimado is not None and result.valor_estimado > 0, (
                "Expected valor_estimado to be populated"
            )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="tender_understanding",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
