"""Eval: blacklist tool (check_blacklist) — real HTTP calls to CGU API.

Run with: pytest -m eval tests/evals/test_blacklist_eval.py
Requires: CGU_API_KEY env var
"""
from __future__ import annotations

import os

import pytest

from src.tools.blacklist import check_blacklist
from tests.evals.conftest import EvalRecorder
from tests.fixtures.blacklist_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_blacklist_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    api_key = os.environ.get("CGU_API_KEY", "")
    if not api_key:
        pytest.skip("CGU_API_KEY not set — skipping live blacklist eval")

    error_msg = None
    result_dict = None
    passed = False

    try:
        result = check_blacklist(case["context"]["company_cnpj"], api_key)
        result_dict = result.model_dump()

        assert result.any_blocked == case["expected_any_blocked"], (
            f"Expected any_blocked={case['expected_any_blocked']}, got {result.any_blocked}"
        )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="blacklist",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
