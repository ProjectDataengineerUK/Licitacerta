from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.read_parse import ReadParseAgent
from src.schemas.tender import PageContent


def _make_raw_gemini(tokens_in: int = 200, tokens_out: int = 500) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_pages() -> list[PageContent]:
    return [
        PageContent(page_number=1, text="Objeto: Papel A4.", tables=[], is_ocr=False),
        PageContent(page_number=2, text="Habilitação.", tables=[], is_ocr=False),
    ]


def _make_parsed_pages(pages=None):
    parsed = MagicMock()
    parsed.pages = pages if pages is not None else _make_pages()
    return parsed


def _make_llm_result(pages=None) -> dict:
    return {
        "parsed": _make_parsed_pages(pages),
        "raw": _make_raw_gemini(),
        "parsing_error": None,
    }


@pytest.fixture()
def read_parse_agent():
    with patch("src.agents.read_parse.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = ReadParseAgent()
    return agent, mock_llm


def test_run_returns_page_list(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"edital_raw": "texto", "run_id": "r1", "tenant_id": "t1"})

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].page_number == 1


def test_run_returns_empty_list(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = _make_llm_result(pages=[])

    result = agent.run({"edital_raw": ""})

    assert result == []


def test_run_raises_on_parse_failure(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = {
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "unexpected EOF",
    }

    with pytest.raises(ValueError, match="ReadParseAgent structured output failed"):
        agent.run({"edital_raw": "texto"})


def test_no_bq_without_gcp_project(read_parse_agent, monkeypatch):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)

    agent.run({"edital_raw": "texto", "run_id": "r1", "tenant_id": "t1"})

    assert agent._bq is None


def test_logs_to_bq_when_configured(read_parse_agent, monkeypatch):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = _make_llm_result()
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    agent._bq = None

    mock_bq = MagicMock()
    with patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq):
        agent.run({"edital_raw": "texto", "run_id": "r1", "tenant_id": "t1"})

    mock_bq.insert_agent_run.assert_called_once()
    call_kwargs = mock_bq.insert_agent_run.call_args[1]
    assert call_kwargs["agent_name"] == "read_parse"
    assert call_kwargs["tokens_in"] == 200
    assert call_kwargs["tokens_out"] == 500


def test_run_auto_generates_run_id(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.invoke.return_value = _make_llm_result()

    result = agent.run({"edital_raw": "texto"})

    assert result is not None


@pytest.mark.asyncio
async def test_arun_returns_page_list(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.ainvoke = AsyncMock(return_value=_make_llm_result())

    result = await agent.arun({"edital_raw": "texto", "run_id": "r1", "tenant_id": "t1"})

    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_arun_raises_on_parse_failure(read_parse_agent):
    agent, mock_llm = read_parse_agent
    mock_llm.ainvoke = AsyncMock(return_value={
        "parsed": None,
        "raw": _make_raw_gemini(),
        "parsing_error": "schema mismatch",
    })

    with pytest.raises(ValueError, match="ReadParseAgent structured output failed"):
        await agent.arun({"edital_raw": "texto"})
