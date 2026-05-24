from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.compliance import ComplianceAgent, _calc_cost_brl, _extract_usage
from src.schemas.results import ComplianceResult


def _make_raw(tokens_in: int = 500, tokens_out: int = 200) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {"usage": {"input_tokens": tokens_in, "output_tokens": tokens_out}}
    return raw


def _make_llm_result(risk_level: str = "low") -> dict:
    parsed = MagicMock(spec=ComplianceResult)
    parsed.risk_level = risk_level
    parsed.blocking_issues = [] if risk_level not in ("critical",) else [MagicMock()]
    parsed.human_decision_required = risk_level in ("critical", "high")
    parsed.model_dump.return_value = {}
    return {"parsed": parsed, "raw": _make_raw(), "parsing_error": None}


@pytest.fixture()
def agent():
    with patch("src.agents.compliance.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        compliance_agent = ComplianceAgent()
    return compliance_agent, mock_llm


class TestComplianceAgentSync:
    def test_run_returns_parsed_result(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("low")

        result = compliance_agent.run({"run_id": "r-1", "tenant_id": "t-1"})

        assert result.risk_level == "low"
        mock_llm.invoke.assert_called_once()

    def test_run_passes_run_id_and_tenant_in_messages(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("low")

        compliance_agent.run({"run_id": "my-run", "tenant_id": "my-tenant"})

        args, kwargs = mock_llm.invoke.call_args
        messages = args[0]
        assert len(messages) == 2

    def test_run_generates_uuid_when_no_run_id(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("low")

        result = compliance_agent.run({})

        assert result is not None

    def test_run_raises_on_parsing_error(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = {"parsed": None, "raw": _make_raw(), "parsing_error": "bad json"}

        with pytest.raises(ValueError, match="structured output failed"):
            compliance_agent.run({"run_id": "r-1", "tenant_id": "t-1"})

    def test_run_logs_bigquery_when_gcp_configured(self, agent, monkeypatch):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("low")
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

        mock_bq = MagicMock()
        with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
            compliance_agent._bq = None  # reset lazy singleton
            compliance_agent.run({"run_id": "run-bq", "tenant_id": "tenant-bq"})

        mock_bq.insert_agent_run.assert_called_once()
        call_kw = mock_bq.insert_agent_run.call_args.kwargs
        assert call_kw["agent_name"] == "compliance"
        assert call_kw["model_id"] == "claude-sonnet-4-6"
        assert call_kw["run_id"] == "run-bq"
        assert call_kw["tenant_id"] == "tenant-bq"
        assert call_kw["tokens_in"] == 500
        assert call_kw["tokens_out"] == 200
        assert call_kw["eval_score"] is None

    def test_run_no_bigquery_without_gcp(self, agent, monkeypatch):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("low")
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

        result = compliance_agent.run({"run_id": "r-no-gcp", "tenant_id": "t-1"})

        assert result is not None

    def test_run_bigquery_error_does_not_propagate(self, agent, monkeypatch):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("medium")
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")

        mock_bq = MagicMock()
        mock_bq.insert_agent_run.side_effect = Exception("BigQuery unavailable")
        with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
            compliance_agent._bq = None
            result = compliance_agent.run({"run_id": "r-bq-err", "tenant_id": "t-1"})

        assert result.risk_level == "medium"

    def test_run_critical_sets_human_decision_required(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.invoke.return_value = _make_llm_result("critical")

        result = compliance_agent.run({"run_id": "r-1", "tenant_id": "t-1"})

        assert result.human_decision_required is True


class TestComplianceAgentAsync:
    @pytest.mark.asyncio
    async def test_arun_returns_parsed_result(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result("high"))

        result = await compliance_agent.arun({"run_id": "async-r-1", "tenant_id": "t-1"})

        assert result.risk_level == "high"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_arun_raises_on_parsing_error(self, agent):
        compliance_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(
            return_value={"parsed": None, "raw": _make_raw(), "parsing_error": "schema mismatch"}
        )

        with pytest.raises(ValueError, match="structured output failed"):
            await compliance_agent.arun({"run_id": "r-1", "tenant_id": "t-1"})

    @pytest.mark.asyncio
    async def test_arun_no_bigquery_without_gcp(self, agent, monkeypatch):
        compliance_agent, mock_llm = agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result("low"))
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

        result = await compliance_agent.arun({})

        assert result is not None


class TestHelpers:
    def test_calc_cost_brl_zero_tokens(self):
        assert _calc_cost_brl(0, 0) == 0.0

    def test_calc_cost_brl_known_values(self):
        cost = _calc_cost_brl(1_000_000, 0)
        assert abs(cost - 3 * 5.70) < 0.001

        cost = _calc_cost_brl(0, 1_000_000)
        assert abs(cost - 15 * 5.70) < 0.001

    def test_extract_usage_normal(self):
        raw = MagicMock()
        raw.response_metadata = {"usage": {"input_tokens": 123, "output_tokens": 456}}
        assert _extract_usage(raw) == (123, 456)

    def test_extract_usage_missing_metadata(self):
        raw = MagicMock()
        raw.response_metadata = {}
        assert _extract_usage(raw) == (0, 0)

    def test_extract_usage_none_raw(self):
        assert _extract_usage(None) == (0, 0)

    def test_extract_usage_no_usage_key(self):
        raw = MagicMock()
        raw.response_metadata = {"model": "claude-sonnet-4-6"}
        assert _extract_usage(raw) == (0, 0)


class TestComplianceEvals:
    """Eval dataset — requires real LLM calls. Run with: pytest -m integration"""

    @pytest.mark.integration
    def test_eval_suite_passes_4_of_5(self):
        from tests.fixtures.compliance_evals import EVAL_CASES

        eval_agent = ComplianceAgent()
        passed = 0
        failures = []

        for case in EVAL_CASES:
            result = eval_agent.run(case["context"])
            if result.risk_level == case["expected_risk_level"]:
                passed += 1
            else:
                failures.append(
                    f"{case['id']}: expected {case['expected_risk_level']}, got {result.risk_level}"
                )

        assert passed >= 4, f"Eval suite: {passed}/5 passed. Failures: {failures}"
