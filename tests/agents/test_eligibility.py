from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.eligibility import (
    EligibilityAgent,
    _calc_cost_gemini_flash,
    _extract_usage_gemini,
)
from src.config import settings
from src.schemas.results import EligibilityResult


def _make_raw_gemini(tokens_in: int = 400, tokens_out: int = 80) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_llm_result(is_eligible: bool = True) -> dict:
    parsed = MagicMock(spec=EligibilityResult)
    parsed.is_eligible = is_eligible
    parsed.blocking_issues = [] if is_eligible else [MagicMock()]
    parsed.missing_documents = []
    parsed.expiring_certifications = []
    parsed.human_decision_required = not is_eligible
    parsed.model_dump.return_value = {}
    return {"parsed": parsed, "raw": _make_raw_gemini(), "parsing_error": None}


@pytest.fixture()
def agent():
    with patch("src.agents.eligibility.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        elig_agent = EligibilityAgent()
    return elig_agent, mock_llm


class TestEligibilityAgentSync:
    def test_run_returns_eligibility_result(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)

        result = elig_agent.run({"run_id": "r-1", "tenant_id": "t-1"})

        assert result.is_eligible is True
        mock_llm.invoke.assert_called_once()

    def test_run_passes_context_in_messages(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)

        elig_agent.run({"run_id": "r-1", "tenant_id": "t-1", "company_cnpj": "12.345.678/0001-99"})

        args, _ = mock_llm.invoke.call_args
        messages = args[0]
        assert len(messages) == 2

    def test_run_generates_uuid_when_no_run_id(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)

        result = elig_agent.run({})

        assert result is not None

    def test_run_raises_on_parsing_error(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = {
            "parsed": None,
            "raw": _make_raw_gemini(),
            "parsing_error": "schema mismatch",
        }

        with pytest.raises(ValueError, match="structured output failed"):
            elig_agent.run({"run_id": "r-1", "tenant_id": "t-1"})

    def test_run_logs_bigquery_when_gcp_configured(self, agent, monkeypatch):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

        mock_bq = MagicMock()
        with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
            elig_agent._bq = None
            elig_agent.run({"run_id": "run-bq", "tenant_id": "tenant-bq"})

        mock_bq.insert_agent_run.assert_called_once()
        call_kw = mock_bq.insert_agent_run.call_args.kwargs
        assert call_kw["agent_name"] == "eligibility"
        assert call_kw["model_id"] == settings.gemini_flash
        assert call_kw["run_id"] == "run-bq"
        assert call_kw["tenant_id"] == "tenant-bq"
        assert call_kw["tokens_in"] == 400
        assert call_kw["tokens_out"] == 80
        assert call_kw["eval_score"] is None

    def test_run_no_bigquery_without_gcp(self, agent, monkeypatch):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

        result = elig_agent.run({"run_id": "r-no-gcp", "tenant_id": "t-1"})

        assert result is not None

    def test_run_bigquery_error_does_not_propagate(self, agent, monkeypatch):
        elig_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result(True)
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

        mock_bq = MagicMock()
        mock_bq.insert_agent_run.side_effect = Exception("BigQuery unavailable")
        with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
            elig_agent._bq = None
            result = elig_agent.run({"run_id": "r-bq-err", "tenant_id": "t-1"})

        assert result.is_eligible is True


class TestEligibilityAgentAsync:
    @pytest.mark.asyncio
    async def test_arun_returns_eligibility_result(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result(True))

        result = await elig_agent.arun({"run_id": "async-r-1", "tenant_id": "t-1"})

        assert result.is_eligible is True
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_arun_raises_on_parsing_error(self, agent):
        elig_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(
            return_value={"parsed": None, "raw": _make_raw_gemini(), "parsing_error": "bad schema"}
        )

        with pytest.raises(ValueError, match="structured output failed"):
            await elig_agent.arun({"run_id": "r-1", "tenant_id": "t-1"})

    @pytest.mark.asyncio
    async def test_arun_no_bigquery_without_gcp(self, agent, monkeypatch):
        elig_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result(False))
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

        result = await elig_agent.arun({})

        assert result is not None


class TestInstantiation:
    def test_no_typeerror_on_instantiation(self):
        """AT-007: EligibilityAgent() instantiates without TypeError — _llm via get_llm, not build_agent(model_id=...)."""
        with patch("src.agents.eligibility.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value = mock_llm
            mock_get_llm.return_value = mock_llm
            elig_agent = EligibilityAgent()

        assert elig_agent is not None
        assert elig_agent._llm is mock_llm


class TestHelpers:
    def test_extract_usage_gemini_normal(self):
        raw = _make_raw_gemini(400, 80)
        assert _extract_usage_gemini(raw) == (400, 80)

    def test_extract_usage_gemini_missing_usage_metadata(self):
        raw = MagicMock()
        raw.response_metadata = {}
        assert _extract_usage_gemini(raw) == (0, 0)

    def test_extract_usage_gemini_none_raw(self):
        assert _extract_usage_gemini(None) == (0, 0)

    def test_extract_usage_gemini_partial_keys(self):
        raw = MagicMock()
        raw.response_metadata = {"usage_metadata": {"prompt_token_count": 123}}
        assert _extract_usage_gemini(raw) == (123, 0)

    def test_calc_cost_gemini_flash_zero(self):
        assert _calc_cost_gemini_flash(0, 0) == 0.0

    def test_calc_cost_gemini_flash_known_values(self):
        cost = _calc_cost_gemini_flash(1_000_000, 0)
        assert abs(cost - 0.075) < 0.0001

        cost = _calc_cost_gemini_flash(0, 1_000_000)
        assert abs(cost - 0.30) < 0.0001


class TestEligibilityEvals:
    """Eval dataset — requires real LLM calls. Run with: pytest -m integration"""

    @pytest.mark.integration
    def test_eval_suite_passes_4_of_5(self):
        from tests.fixtures.eligibility_evals import EVAL_CASES

        eval_agent = EligibilityAgent()
        passed = 0
        failures = []

        for case in EVAL_CASES:
            result = eval_agent.run(case["context"])
            if result.is_eligible == case["expected_is_eligible"]:
                passed += 1
            else:
                failures.append(
                    f"{case['id']}: expected is_eligible={case['expected_is_eligible']}, "
                    f"got {result.is_eligible}"
                )

        assert passed >= 4, f"Eval suite: {passed}/5 passed. Failures: {failures}"
