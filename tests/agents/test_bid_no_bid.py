from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.bid_no_bid import BidNoBidAgent
from src.schemas.results import BidDecision


def _make_raw_gemini(tokens_in: int = 600, tokens_out: int = 150) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_parsed(recommendation: str = "participar") -> MagicMock:
    parsed = MagicMock(spec=BidDecision)
    parsed.recommendation = recommendation
    parsed.risk_level = "low"
    parsed.expected_margin_pct = 18.0
    parsed.human_decision_required = False
    parsed.recommended_action = "Participar com preço realista"
    return parsed


def _make_llm_result(recommendation: str = "participar") -> dict:
    return {
        "parsed": _make_parsed(recommendation),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def bid_agent():
    with patch("src.agents.bid_no_bid.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = BidNoBidAgent()
    return agent, mock_llm


def test_bid_run_returns_parsed(bid_agent):
    agent, mock_llm = bid_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert result.recommendation == "participar"
    assert result.risk_level == "low"


def test_bid_run_raises_on_parse_failure(bid_agent):
    agent, mock_llm = bid_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    }

    with pytest.raises(ValueError, match="BidNoBidAgent structured output failed"):
        agent.run({})


def test_bid_messages_include_all_context_keys(bid_agent):
    agent, mock_llm = bid_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({
        "tender_schema": "ts",
        "eligibility": "el",
        "compliance": "co",
        "blacklist": "bl",
        "pricing": "pr",
    })

    messages = mock_llm.invoke.call_args[0][0]
    human_text = messages[1].content
    assert "tender_schema" in human_text
    assert "eligibility" in human_text
    assert "compliance" in human_text
    assert "blacklist" in human_text
    assert "pricing" in human_text


def test_bid_no_bq_without_gcp_project(bid_agent, monkeypatch):
    agent, mock_llm = bid_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_bid_logs_to_bq_when_gcp_configured(bid_agent, monkeypatch):
    agent, mock_llm = bid_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "bid_no_bid"
    assert call_kwargs["tokens_in"] == 600
    assert call_kwargs["tokens_out"] == 150


@pytest.mark.asyncio
async def test_bid_arun_returns_parsed(bid_agent):
    agent, mock_llm = bid_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result("participar_com_ressalvas"))

    result = await agent.arun({"run_id": "r1", "tenant_id": "t1"})

    assert result.recommendation == "participar_com_ressalvas"
