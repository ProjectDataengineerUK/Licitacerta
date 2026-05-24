from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.watch import WatchAgent, WatchAlert, WatchResult


def _make_raw_gemini(tokens_in: int = 500, tokens_out: int = 120) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_parsed() -> MagicMock:
    parsed = MagicMock(spec=WatchResult)
    parsed.alerts = [
        WatchAlert(
            alert_type="prazo_vencendo",
            urgency="high",
            description="Sessão de pregão em 2 dias",
            deadline="2026-05-26T10:00:00",
            recommended_action="Confirmar habilitação",
            human_decision_required=True,
        )
    ]
    parsed.next_deadline = "2026-05-26T10:00:00"
    parsed.summary = "Pregão se aproxima — ação necessária"
    return parsed


def _make_llm_result() -> dict:
    return {
        "parsed": _make_parsed(),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def watch_agent():
    with patch("src.agents.watch.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = WatchAgent()
    return agent, mock_llm


def test_watch_run_returns_result(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert result.summary == "Pregão se aproxima — ação necessária"
    assert len(result.alerts) == 1


def test_watch_run_raises_on_parse_failure(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    }

    with pytest.raises(ValueError, match="WatchAgent structured output failed"):
        agent.run({})


def test_watch_no_bq_without_gcp_project(watch_agent, monkeypatch):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_watch_logs_to_bq_with_agent_name(watch_agent, monkeypatch):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "watch"
    assert call_kwargs["tokens_in"] == 500
    assert call_kwargs["tokens_out"] == 120


def test_watch_messages_include_all_context_keys(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({
        "tender_schema": "ts",
        "proposal_draft": "pd",
        "monitoring_data": "md",
    })

    messages = mock_llm.invoke.call_args[0][0]
    human_text = messages[1].content
    assert "tender_schema" in human_text
    assert "proposal_draft" in human_text
    assert "monitoring_data" in human_text


def test_watch_auto_run_id(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.invoke.return_value = _make_llm_result()

    agent.run({})

    mock_llm.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_watch_arun_returns_result(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result())

    result = await agent.arun({"run_id": "r1", "tenant_id": "t1"})

    assert result.summary == "Pregão se aproxima — ação necessária"


@pytest.mark.asyncio
async def test_watch_arun_raises_on_parse_failure(watch_agent):
    agent, mock_llm = watch_agent
    mock_llm.ainvoke = AsyncMock(return_value={
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "validation error",
    })

    with pytest.raises(ValueError, match="WatchAgent structured output failed"):
        await agent.arun({})
