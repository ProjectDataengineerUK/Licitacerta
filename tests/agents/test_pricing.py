from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.pricing import PricingAgent
from src.schemas.results import PricingResult


def _make_raw_gemini(tokens_in: int = 400, tokens_out: int = 120) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_parsed() -> MagicMock:
    parsed = MagicMock(spec=PricingResult)
    parsed.recommended_price = Decimal("97560.98")
    parsed.min_margin_pct = 18.0
    parsed.blocking_issues = []
    parsed.human_decision_required = False
    parsed.recommended_action = "Usar preço realista"
    return parsed


def _make_llm_result(parsed=None) -> dict:
    return {
        "parsed": parsed or _make_parsed(),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def pricing_agent():
    with patch("src.agents.pricing.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = PricingAgent()
    return agent, mock_llm


def test_pricing_run_returns_parsed(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"company_cnpj": "12345678000195", "run_id": "r1", "tenant_id": "t1"})

    assert isinstance(result, MagicMock)
    assert result.recommended_price == Decimal("97560.98")
    assert result.min_margin_pct == 18.0


def test_pricing_run_raises_on_parse_failure(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "unexpected token",
    }

    with pytest.raises(ValueError, match="PricingAgent structured output failed"):
        agent.run({"company_cnpj": "12345678000195"})


def test_pricing_messages_include_context_keys(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({
        "company_cnpj": "12345678000195",
        "tender_schema": "ts",
        "eligibility": "el",
        "compliance": "co",
        "blacklist": "bl",
    })

    messages = mock_llm.invoke.call_args[0][0]
    human_text = messages[1].content
    assert "company_cnpj" in human_text
    assert "tender_schema" in human_text
    assert "eligibility" in human_text
    assert "compliance" in human_text
    assert "blacklist" in human_text


def test_pricing_auto_generates_run_id(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"company_cnpj": "12345678000195"})

    assert result is not None


def test_pricing_no_bq_without_gcp_project(pricing_agent, monkeypatch):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"company_cnpj": "12345678000195", "run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_pricing_logs_to_bq_when_gcp_configured(pricing_agent, monkeypatch):
    agent, mock_llm = pricing_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"company_cnpj": "12345678000195", "run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "pricing"
    assert call_kwargs["tokens_in"] == 400
    assert call_kwargs["tokens_out"] == 120


@pytest.mark.asyncio
async def test_pricing_arun_returns_parsed(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result())

    result = await agent.arun({"company_cnpj": "12345678000195", "run_id": "r1", "tenant_id": "t1"})

    assert result.recommended_price == Decimal("97560.98")


@pytest.mark.asyncio
async def test_pricing_arun_raises_on_parse_failure(pricing_agent):
    agent, mock_llm = pricing_agent
    mock_llm.ainvoke = AsyncMock(return_value={
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "schema mismatch",
    })

    with pytest.raises(ValueError, match="PricingAgent structured output failed"):
        await agent.arun({"company_cnpj": "12345678000195"})
