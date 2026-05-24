from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.tender_understanding import (
    TenderUnderstandingAgent,
    _calc_cost_gemini_pro,
    _extract_usage_gemini,
)
from src.config import settings


def _make_raw_gemini(tokens_in: int = 350, tokens_out: int = 90) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_tu_result() -> dict:
    from src.schemas.tender import TenderSchema
    parsed = MagicMock(spec=TenderSchema)
    parsed.objeto = "Aquisição de computadores"
    parsed.orgao = "Prefeitura"
    parsed.modalidade = "pregao_eletronico"
    parsed.criterio_julgamento = "menor_preco"
    parsed.documentos_exigidos = ["CNPJ ativo"]
    parsed.exigencias_tecnicas = []
    parsed.penalidades = []
    parsed.evidence = []
    parsed.model_dump.return_value = {}
    return {"parsed": parsed, "raw": _make_raw_gemini(), "parsing_error": None}


@pytest.fixture()
def tu_agent():
    with patch("src.agents.tender_understanding.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = TenderUnderstandingAgent()
    return agent, mock_llm


class TestInstantiation:
    def test_no_typeerror_on_instantiation(self):
        with patch("src.agents.tender_understanding.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value = mock_llm
            mock_get_llm.return_value = mock_llm
            agent = TenderUnderstandingAgent()
        assert agent is not None
        assert agent._llm is mock_llm

    def test_uses_model_tier_analyze(self):
        from src.agents.model_router import ModelTier
        with patch("src.agents.tender_understanding.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value = mock_llm
            mock_get_llm.return_value = mock_llm
            TenderUnderstandingAgent()
        mock_get_llm.assert_called_once_with(ModelTier.ANALYZE)


class TestRun:
    def test_run_returns_tender_schema(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()

        result = agent.run({"edital_pages": "texto do edital", "edital_id": "edital-001"})

        assert result.objeto == "Aquisição de computadores"

    def test_run_passes_edital_pages_in_messages(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()

        agent.run({"edital_pages": "texto pagina 1", "edital_id": "e-001"})

        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        assert len(messages) == 2
        assert "texto pagina 1" in messages[1].content

    def test_run_generates_uuid_when_no_run_id(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()

        result = agent.run({"edital_pages": "texto"})

        assert result is not None

    def test_run_raises_on_parsing_error(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = {
            "parsed": None,
            "raw": _make_raw_gemini(),
            "parsing_error": "schema mismatch",
        }

        with pytest.raises(ValueError, match="structured output failed"):
            agent.run({"edital_pages": "texto"})

    def test_run_logs_bigquery_when_gcp_configured(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()
        mock_bq = MagicMock()

        with (
            patch.dict("os.environ", {"GCP_PROJECT_ID": "proj-test"}),
            patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq),
        ):
            agent._bq = None
            agent.run({
                "edital_pages": "texto",
                "run_id": "run-123",
                "tenant_id": "tenant-abc",
            })

        mock_bq.insert_agent_run.assert_called_once()
        call_kwargs = mock_bq.insert_agent_run.call_args.kwargs
        assert call_kwargs["agent_name"] == "tender_understanding"
        assert call_kwargs["model_id"] == settings.gemini_pro
        assert call_kwargs["run_id"] == "run-123"
        assert call_kwargs["tenant_id"] == "tenant-abc"

    def test_run_no_bigquery_without_gcp(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()

        with patch.dict("os.environ", {}, clear=True):
            result = agent.run({"edital_pages": "texto"})

        assert result is not None

    def test_run_bigquery_error_does_not_propagate(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.invoke.return_value = _make_tu_result()
        mock_bq = MagicMock()
        mock_bq.insert_agent_run.side_effect = RuntimeError("BQ down")

        with (
            patch.dict("os.environ", {"GCP_PROJECT_ID": "proj-test"}),
            patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq),
        ):
            agent._bq = None
            result = agent.run({"edital_pages": "texto"})

        assert result is not None


class TestArun:
    @pytest.mark.asyncio
    async def test_arun_returns_tender_schema(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_tu_result())

        result = await agent.arun({"edital_pages": "texto do edital async"})

        assert result.objeto == "Aquisição de computadores"

    @pytest.mark.asyncio
    async def test_arun_raises_on_parsing_error(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.ainvoke = AsyncMock(return_value={
            "parsed": None,
            "raw": _make_raw_gemini(),
            "parsing_error": "schema mismatch",
        })

        with pytest.raises(ValueError, match="structured output failed"):
            await agent.arun({"edital_pages": "texto"})

    @pytest.mark.asyncio
    async def test_arun_no_bigquery_without_gcp(self, tu_agent):
        agent, mock_llm = tu_agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_tu_result())

        with patch.dict("os.environ", {}, clear=True):
            result = await agent.arun({"edital_pages": "texto"})

        assert result is not None


class TestHelpers:
    def test_extract_usage_gemini_normal(self):
        raw = _make_raw_gemini(tokens_in=350, tokens_out=90)
        assert _extract_usage_gemini(raw) == (350, 90)

    def test_extract_usage_gemini_missing_key(self):
        raw = MagicMock()
        raw.response_metadata = {}
        assert _extract_usage_gemini(raw) == (0, 0)

    def test_extract_usage_gemini_exception(self):
        raw = MagicMock()
        raw.response_metadata = None
        assert _extract_usage_gemini(raw) == (0, 0)

    def test_calc_cost_gemini_pro_zero(self):
        assert _calc_cost_gemini_pro(0, 0) == 0.0

    def test_calc_cost_gemini_pro_known_values(self):
        # 1M input + 1M output = ($1.25 + $5.00) = $6.25
        result = _calc_cost_gemini_pro(1_000_000, 1_000_000)
        assert abs(result - 6.25) < 1e-9

    def test_calc_cost_gemini_pro_typical_run(self):
        # 10K input + 2K output = (12500 + 10000) / 1e6 = $0.0225
        result = _calc_cost_gemini_pro(10_000, 2_000)
        assert abs(result - 0.02250) < 1e-9
