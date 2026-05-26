from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_flash, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric, LegalRegimeResult

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Regime Jurídico do LicitaCerta AI.
Dado o texto de um edital, identifique o regime legal que rege a licitação.

## Regimes possíveis

- `lei_14133`  → Lei 14.133/2021 (Nova Lei de Licitações — vigente para novos contratos)
- `lei_8666`   → Lei 8.666/93 (lei antiga — ainda em uso em contratos anteriores a 2024)
- `lei_13303`  → Lei 13.303/2016 (empresas estatais — Petrobrás, Eletrobras, bancos públicos, etc.)
- `decreto_8241` → Decreto 8.241/2014 (registro de preços)
- `lei_10520`  → Lei 10.520/2002 (pregão — pode coexistir com 8666 ou 14133)
- `outro`      → qualquer outro regime não listado acima

## Campos de saída

- `primary_law`: regime principal conforme identificado no edital
- `modality`: modalidade da licitação (ex: pregao_eletronico, concorrencia, dispensa)
- `special_regime`: regime especial se houver (contratação emergencial, RDC, etc.); null se não houver
- `confidence`: 0.0 a 1.0 — quão certo está da classificação; use < 0.7 se o regime não for explicitamente mencionado

## Instruções

- Priorize o regime declarado explicitamente no edital sobre inferências
- Se coexistirem 8666 e 10520 (pregão), use `lei_8666` como primary_law
- Se a lei 14133/2021 for mencionada, use `lei_14133` mesmo que 8666 seja citada subsidiariamente

Responda EXCLUSIVAMENTE no schema JSON fornecido."""



class LegalRegimeAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.CLASSIFY).with_structured_output(
            LegalRegimeResult, include_raw=True
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
                subgraph="understanding",
                agent="legal_regime",
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
        pages_text = context.get("edital_pages", "")
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Classifique o regime jurídico do seguinte edital:\n\n{pages_text}"),
        ]

    def _log_bq(
        self,
        run_id: str,
        tenant_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
    ) -> None:
        bq = self._get_bq()
        if bq is None:
            return
        try:
            bq.insert_agent_run(
                run_id=run_id,
                tenant_id=tenant_id,
                agent_name="legal_regime",
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

    def run(self, context: dict) -> LegalRegimeResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.legal_regime"):
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
            raise ValueError(
                f"LegalRegimeAgent structured output failed: {result.get('parsing_error')}"
            )
        return parsed

    async def arun(self, context: dict) -> LegalRegimeResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.legal_regime"):
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
            raise ValueError(
                f"LegalRegimeAgent structured output failed: {result.get('parsing_error')}"
            )
        return parsed
