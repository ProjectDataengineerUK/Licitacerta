from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.proposal import ProposalAgent
from src.schemas.results import ProposalDraft


def _make_raw_gemini(tokens_in: int = 800, tokens_out: int = 400) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_parsed() -> MagicMock:
    parsed = MagicMock(spec=ProposalDraft)
    parsed.content = "PROPOSTA COMERCIAL\n\nEmpresa: ACME LTDA\nPreço: R$ 47.058,82"
    parsed.price = Decimal("47058.82")
    parsed.validity_days = 60
    parsed.attachments = ["cnpj.pdf", "cnd_federal.pdf"]
    parsed.generated_at = datetime.utcnow()
    parsed.approved_by = "jonatas"
    return parsed


def _make_llm_result() -> dict:
    return {
        "parsed": _make_parsed(),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def proposal_agent():
    with patch("src.agents.proposal.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = ProposalAgent()
    return agent, mock_llm


def test_proposal_run_returns_draft(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert result.price == Decimal("47058.82")
    assert result.validity_days == 60


def test_proposal_run_raises_on_parse_failure(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    }

    with pytest.raises(ValueError, match="ProposalAgent structured output failed"):
        agent.run({})


def test_proposal_no_bq_without_gcp_project(proposal_agent, monkeypatch):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_proposal_logs_to_bq_with_agent_name(proposal_agent, monkeypatch):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "proposal"
    assert "gemini" in call_kwargs["model_id"]
    assert call_kwargs["tokens_in"] == 800
    assert call_kwargs["tokens_out"] == 400


def test_proposal_messages_include_all_context_keys(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({
        "tender_schema": "ts",
        "pricing": "pr",
        "bid_decision": "bd",
        "human_approvals": "ha",
    })

    messages = mock_llm.invoke.call_args[0][0]
    human_text = messages[1].content
    assert "tender_schema" in human_text
    assert "pricing" in human_text
    assert "bid_decision" in human_text
    assert "human_approvals" in human_text


def test_proposal_auto_run_id(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({})

    mock_llm.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_proposal_arun_returns_draft(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result())

    result = await agent.arun({"run_id": "r1", "tenant_id": "t1"})

    assert result.price == Decimal("47058.82")


@pytest.mark.asyncio
async def test_proposal_arun_raises_on_parse_failure(proposal_agent):
    agent, mock_llm = proposal_agent
    mock_llm.ainvoke = AsyncMock(return_value={
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    })

    with pytest.raises(ValueError, match="ProposalAgent structured output failed"):
        await agent.arun({})
