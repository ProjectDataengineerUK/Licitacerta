from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.compliance import ComplianceAgent
from src.schemas.results import ComplianceResult
from src.tools.juridical_search import JuridicalChunk, _NoOpJuridicalSearchTool


def _make_chunk(numero: str = "2500/2015-Plenario") -> JuridicalChunk:
    return JuridicalChunk(
        id="uid-1", tipo="acordao", numero=numero,
        fonte="TCU", texto=f"Texto do acórdão {numero}.", score=0.92,
    )


def _make_compliance_result(**kwargs) -> ComplianceResult:
    defaults = dict(
        conclusion="Edital analisado.",
        confidence=0.8,
        recommended_action="participar",
        risk_level="low",
    )
    return ComplianceResult(**{**defaults, **kwargs})


def _mock_llm(result: ComplianceResult):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = {"parsed": result, "raw": MagicMock(response_metadata={"usage": {}})}
    mock_llm.ainvoke = AsyncMock(
        return_value={"parsed": result, "raw": MagicMock(response_metadata={"usage": {}})}
    )
    return mock_llm


def _make_agent(llm, rag_tool=None) -> ComplianceAgent:
    agent = ComplianceAgent.__new__(ComplianceAgent)
    import threading
    agent._llm = llm
    agent._bq = None
    agent._last_metric = None
    agent._metric_lock = threading.Lock()
    agent._rag_tool = rag_tool or _NoOpJuridicalSearchTool()
    return agent


def test_at004_run_with_rag_sets_juridical_context_used():
    chunks = [_make_chunk("2500/2015-Plenario"), _make_chunk("936/2011-Plenario")]
    fake_tool = MagicMock()
    fake_tool.search.return_value = chunks
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed), rag_tool=fake_tool)

    result = agent.run({"tender_schema": None, "run_id": "r1"})

    assert result.juridical_context_used is True
    # LLM must have been invoked with 3 messages (system + rag_context + analysis)
    messages = agent._llm.invoke.call_args[0][0]
    assert len(messages) == 3
    assert "Jurisprudência" in messages[1].content


def test_run_without_rag_chunks_has_two_messages():
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed))

    result = agent.run({"tender_schema": None, "run_id": "r1"})

    assert result.juridical_context_used is False
    messages = agent._llm.invoke.call_args[0][0]
    assert len(messages) == 2


def test_at005_run_rag_search_raises_does_not_propagate():
    fake_tool = MagicMock()
    fake_tool.search.side_effect = Exception("db down")
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed), rag_tool=fake_tool)

    result = agent.run({"tender_schema": None, "run_id": "r1"})

    assert result.juridical_context_used is False
    messages = agent._llm.invoke.call_args[0][0]
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_at004_arun_with_rag_sets_juridical_context_used():
    chunks = [_make_chunk("1284/2023-Plenario")]
    fake_tool = MagicMock()
    fake_tool.asearch = AsyncMock(return_value=chunks)
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed), rag_tool=fake_tool)

    result = await agent.arun({"tender_schema": None, "run_id": "r1"})

    assert result.juridical_context_used is True
    messages = agent._llm.ainvoke.call_args[0][0]
    assert len(messages) == 3


@pytest.mark.asyncio
async def test_at006_arun_rag_timeout_returns_valid_result():
    import asyncio as _asyncio

    fake_tool = MagicMock()
    fake_tool.asearch = AsyncMock(side_effect=_asyncio.TimeoutError())
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed), rag_tool=fake_tool)

    result = await agent.arun({"tender_schema": None, "run_id": "r1"})

    assert result.juridical_context_used is False
    messages = agent._llm.ainvoke.call_args[0][0]
    assert len(messages) == 2


def test_lazy_init_rag_tool_called_once():
    parsed = _make_compliance_result()
    agent = _make_agent(_mock_llm(parsed))
    agent._rag_tool = None  # reset to trigger lazy init

    class CountingNoOp(_NoOpJuridicalSearchTool):
        pass

    with patch("src.tools.juridical_search.JuridicalSearchTool.from_env",
               return_value=CountingNoOp()) as mock_from_env:
        agent.run({"tender_schema": None, "run_id": "r1"})
        agent.run({"tender_schema": None, "run_id": "r2"})

    mock_from_env.assert_called_once()


def test_juridical_context_used_default_false():
    r = _make_compliance_result()
    assert r.juridical_context_used is False
