from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.contract import ContractAgent, ContractObligation, ContractResult


def _make_raw_gemini(tokens_in: int = 700, tokens_out: int = 250) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_parsed() -> MagicMock:
    parsed = MagicMock(spec=ContractResult)
    parsed.contract_status = "active"
    parsed.obligations = [
        ContractObligation(
            description="Entrega dos materiais",
            due_date="2026-06-22",
            recurrent=False,
            status="pending",
        )
    ]
    parsed.next_payment_date = "2026-07-25"
    parsed.reajuste_due = False
    parsed.reajuste_index = None
    parsed.warnings = ["Prazo de entrega em 30 dias"]
    parsed.human_decision_required = False
    parsed.recommended_action = "Iniciar preparação da entrega"
    return parsed


def _make_llm_result() -> dict:
    return {
        "parsed": _make_parsed(),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def contract_agent():
    with patch("src.agents.contract.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = ContractAgent()
    return agent, mock_llm


def test_contract_run_returns_result(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert result.contract_status == "active"
    assert len(result.obligations) == 1


def test_contract_run_raises_on_parse_failure(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    }

    with pytest.raises(ValueError, match="ContractAgent structured output failed"):
        agent.run({})


def test_contract_no_bq_without_gcp_project(contract_agent, monkeypatch):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_contract_logs_to_bq_with_agent_name(contract_agent, monkeypatch):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "contract"
    assert "gemini" in call_kwargs["model_id"]
    assert call_kwargs["tokens_in"] == 700
    assert call_kwargs["tokens_out"] == 250


def test_contract_messages_include_all_context_keys(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({
        "tender_schema": "ts",
        "proposal_draft": "pd",
        "contract_data": "cd",
    })

    messages = mock_llm.invoke.call_args[0][0]
    human_text = messages[1].content
    assert "tender_schema" in human_text
    assert "proposal_draft" in human_text
    assert "contract_data" in human_text


def test_contract_auto_run_id(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({})

    mock_llm.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_contract_arun_returns_result(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result())

    result = await agent.arun({"run_id": "r1", "tenant_id": "t1"})

    assert result.contract_status == "active"


@pytest.mark.asyncio
async def test_contract_arun_raises_on_parse_failure(contract_agent):
    agent, mock_llm = contract_agent
    mock_llm.ainvoke = AsyncMock(return_value={
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    })

    with pytest.raises(ValueError, match="ContractAgent structured output failed"):
        await agent.arun({})
