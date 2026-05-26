from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agents._gemini_utils import _calc_cost_gemini_flash, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric
from src.schemas.tender import PageContent

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter


class _ParsedPages(BaseModel):
    pages: list[PageContent]


SYSTEM_PROMPT = """Você é o Agente de Leitura e Extração do LicitaCerta AI.
Dado o texto bruto de um edital de licitação já segmentado por página,
estruture cada página no formato PageContent com:
- page_number: número da página (1-indexado)
- text: texto limpo da página
- tables: lista de dicionários representando tabelas encontradas (vazia se não houver)
- is_ocr: false (o texto já foi extraído diretamente do PDF)

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class ReadParseAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.EXTRACT).with_structured_output(
            _ParsedPages, include_raw=True
        )
        self._bq: BigQueryWriter | None = None
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()

    def _set_last_metric(
        self,
        *,
        tokens_in: int,
        tokens_out: int,
        cost_brl: float,
        latency_ms: int,
        model_id: str,
    ) -> None:
        with self._metric_lock:
            self._last_metric = AgentMetric(
                subgraph="ingestion",
                agent="read_parse",
                metric_name="cost_brl",
                value=cost_brl,
                timestamp=datetime.utcnow(),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_brl=cost_brl,
                latency_ms=latency_ms,
                model_id=model_id,
            )

    def get_last_metric(self) -> AgentMetric | None:
        with self._metric_lock:
            m = self._last_metric
            self._last_metric = None
            return m

    def _get_bq(self) -> BigQueryWriter | None:
        if not os.environ.get("GCP_PROJECT_ID"):
            return None
        if self._bq is None:
            from src.gcp.bigquery import BigQueryWriter
            self._bq = BigQueryWriter.from_env()
        return self._bq

    def _otel_span(self, name: str) -> Any:
        try:
            from opentelemetry import trace
            return trace.get_tracer("licitacerta.agents").start_as_current_span(name)
        except Exception:
            return contextlib.nullcontext()

    def _build_messages(self, context: dict) -> list:
        edital_raw = context.get("edital_raw", "")
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Extraia as páginas do seguinte edital:\n\n{edital_raw}"),
        ]

    def _log_bq(self, run_id: str, tenant_id: str, tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        bq = self._get_bq()
        if bq is None:
            return
        try:
            bq.insert_agent_run(
                run_id=run_id,
                tenant_id=tenant_id,
                agent_name="read_parse",
                model_id=settings.gemini_flash,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_gemini_flash(tokens_in, tokens_out),
                eval_score=None,
            )
        except Exception:
            pass

    def _get_callbacks(self, run_id: str) -> list:
        try:
            handler = get_langfuse_handler(run_id)
            return [handler] if handler else []
        except Exception:
            return []

    def run(self, context: dict) -> list[PageContent]:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.read_parse"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_flash(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_flash,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ReadParseAgent structured output failed: {result.get('parsing_error')}")
        return parsed.pages

    async def arun(self, context: dict) -> list[PageContent]:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.read_parse"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_flash(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_flash,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ReadParseAgent structured output failed: {result.get('parsing_error')}")
        return parsed.pages
