"""Eval: ReadParseAgent — real LLM calls, incur API cost.

Run with: pytest -m eval tests/evals/test_read_parse_eval.py
"""
from __future__ import annotations

import pytest

from src.agents.read_parse import ReadParseAgent
from tests.evals.conftest import EvalRecorder
from tests.fixtures.read_parse_evals import EVAL_CASES


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_read_parse_eval(case: dict, eval_recorder: EvalRecorder) -> None:
    agent = ReadParseAgent()
    error_msg = None
    result_dict = None
    passed = False

    try:
        pages = agent.run(case["context"])
        result_dict = {"pages_count": len(pages), "first_page_text_len": len(pages[0].text) if pages else 0}

        assert len(pages) >= case["expected_pages_min"], (
            f"Expected at least {case['expected_pages_min']} pages, got {len(pages)}"
        )
        if case["expected_has_objeto"]:
            all_text = " ".join(p.text for p in pages).lower()
            assert any(kw in all_text for kw in ["objeto", "aquisição", "contratação", "prestação", "fornecimento"]), (
                "Expected edital 'objeto' keywords in parsed text"
            )
        passed = True
    except Exception as exc:
        error_msg = str(exc)
        raise
    finally:
        eval_recorder.record(
            agent="read_parse",
            eval_id=case["id"],
            description=case["description"],
            passed=passed,
            result=result_dict,
            error=error_msg,
        )
