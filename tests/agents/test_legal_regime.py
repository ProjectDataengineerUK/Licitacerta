from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.legal_regime import (
    LegalRegimeAgent,
    _calc_cost_gemini_flash,
    _extract_usage_gemini,
)
from src.config import settings
from src.schemas.results import LegalRegimeResult


def _make_raw_gemini(tokens_in: int = 200, tokens_out: int = 40) -> MagicMock:
    raw = MagicMock()
    raw.response_metadata = {
        "usage_metadata": {
            "prompt_token_count": tokens_in,
            "candidates_token_count": tokens_out,
        }
    }
    return raw


def _make_lr_result(primary_law: str = "lei_14133") -> dict:
    parsed = MagicMock(spec=LegalRegimeResult)
    parsed.primary_law = primary_law
    parsed.modality = "pregao_eletronico"
    parsed.special_regime = None
    parsed.confidence = 0.95
    parsed.model_dump.return_value = {}
    return {"parsed": parsed, "raw": _make_raw_gemini(), "parsing_error": None}


@pytest.fixture()
def lr_agent():
    with patch("src.agents.legal_regime.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_llm
        mock_get_llm.return_value = mock_llm
        agent = LegalRegimeAgent()
    return agent, mock_llm


class TestInstantiation:
    def test_no_typeerror_on_instantiation(self):
        with patch("src.agents.legal_regime.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value = mock_llm
            mock_get_llm.return_value = mock_llm
            agent = LegalRegimeAgent()
        assert agent is not None
        assert agent._llm is mock_llm

    def test_uses_model_tier_classify(self):
        from src.agents.model_router import ModelTier
        with patch("src.agents.legal_regime.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.with_structured_output.return_value = mock_llm
            mock_get_llm.return_value = mock_llm
            LegalRegimeAgent()
        mock_get_llm.assert_called_once_with(ModelTier.CLASSIFY)


class TestRun:
    def test_run_returns_legal_regime_result(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = _make_lr_result("lei_14133")

        result = agent.run({"edital_pages": "texto do edital"})

        assert result.primary_law == "lei_14133"

    def test_run_generates_uuid_when_no_run_id(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = _make_lr_result()

        result = agent.run({"edital_pages": "texto"})

        assert result is not None

    def test_run_raises_on_parsing_error(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = {
            "parsed": None,
            "raw": _make_raw_gemini(),
            "parsing_error": "schema mismatch",
        }

        with pytest.raises(ValueError, match="structured output failed"):
            agent.run({"edital_pages": "texto"})

    def test_run_logs_bigquery_when_gcp_configured(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = _make_lr_result()
        mock_bq = MagicMock()

        with (
            patch.dict("os.environ", {"GCP_PROJECT_ID": "proj-test"}),
            patch("src.gcp.bigquery.BigQueryWriter.from_env", return_value=mock_bq),
        ):
            agent._bq = None
            result = agent.run({
                "edital_pages": "texto",
                "run_id": "run-456",
                "tenant_id": "tenant-xyz",
            })

        mock_bq.insert_agent_run.assert_called_once()
        call_kwargs = mock_bq.insert_agent_run.call_args.kwargs
        assert call_kwargs["agent_name"] == "legal_regime"
        assert call_kwargs["model_id"] == settings.gemini_flash
        assert call_kwargs["run_id"] == "run-456"
        assert call_kwargs["tenant_id"] == "tenant-xyz"

    def test_run_no_bigquery_without_gcp(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = _make_lr_result()

        with patch.dict("os.environ", {}, clear=True):
            result = agent.run({"edital_pages": "texto"})

        assert result is not None

    def test_run_bigquery_error_does_not_propagate(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.invoke.return_value = _make_lr_result()
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
    async def test_arun_returns_legal_regime_result(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_lr_result("lei_8666"))

        result = await agent.arun({"edital_pages": "texto async"})

        assert result.primary_law == "lei_8666"

    @pytest.mark.asyncio
    async def test_arun_no_bigquery_without_gcp(self, lr_agent):
        agent, mock_llm = lr_agent
        mock_llm.ainvoke = AsyncMock(return_value=_make_lr_result())

        with patch.dict("os.environ", {}, clear=True):
            result = await agent.arun({"edital_pages": "texto"})

        assert result is not None


class TestHelpers:
    def test_extract_usage_gemini_normal(self):
        raw = _make_raw_gemini(tokens_in=200, tokens_out=40)
        assert _extract_usage_gemini(raw) == (200, 40)

    def test_extract_usage_gemini_missing_key(self):
        raw = MagicMock()
        raw.response_metadata = {}
        assert _extract_usage_gemini(raw) == (0, 0)

    def test_calc_cost_gemini_flash_known_values(self):
        # 1M input + 1M output = ($0.075 + $0.30) = $0.375
        result = _calc_cost_gemini_flash(1_000_000, 1_000_000)
        assert abs(result - 0.375) < 1e-9

    def test_calc_cost_gemini_flash_zero(self):
        assert _calc_cost_gemini_flash(0, 0) == 0.0
