from __future__ import annotations

import contextlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_pro, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric
from src.schemas.tender import TenderSchema

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Entendimento de Editais do LicitaCerta AI.
Dado o texto extraído de um edital de licitação (lista de páginas com seus conteúdos),
extraia as informações estruturadas do edital no schema fornecido.

## Regras de extração

- `objeto`: descrição concisa e específica do que está sendo licitado (máx 200 chars)
- `orgao`: nome completo do órgão licitante conforme consta no edital
- `modalidade`: um de [pregao_eletronico, pregao_presencial, concorrencia, tomada_precos, convite,
  dispensa, inexigibilidade, leilao, dialogo_competitivo]
- `valor_estimado`: em reais, sem formatação (ex: 150000.00); null se não informado explicitamente
- `criterio_julgamento`: um de [menor_preco, maior_desconto, melhor_tecnica, tecnica_e_preco,
  maior_lance, menor_taxa]
- `documentos_exigidos`: liste TODOS os documentos de habilitação exigidos
  (habilitação jurídica, técnica, fiscal, econômica)
- `exigencias_tecnicas`: qualificações técnicas além de documentos padrão
  (atestados específicos, registros profissionais, equipe técnica)
- `penalidades`: multas, sanções e penalidades previstas no instrumento convocatório
- `garantia_exigida`: true se exigida garantia de proposta ou de execução
- `garantia_percentual`: percentual de garantia se informado; null caso contrário
- `prazo_entrega_dias`: prazo de entrega ou execução em dias; null se não informado
- `evidence`: cite pelo menos 3 trechos com número de página exato que sustentam os campos extraídos

## Instruções gerais

- Se uma informação não constar explicitamente no texto, retorne null (não invente)
- Para `documentos_exigidos`, inclua apenas os efetivamente exigidos para habilitação
- Para `evidence`, prefira trechos que fundamentem `objeto`, `modalidade` e `documentos_exigidos`

Responda EXCLUSIVAMENTE no schema JSON fornecido."""



class TenderUnderstandingAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.ANALYZE).with_structured_output(
            TenderSchema, include_raw=True
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
                agent="tender_understanding",
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
        edital_id = context.get("edital_id", "")
        content = f"Edital ID: {edital_id}\n\n{pages_text}"
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=content),
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
                agent_name="tender_understanding",
                model_id=settings.gemini_pro,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
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

    def run(self, context: dict) -> TenderSchema:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.tender_understanding"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_pro,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(
                f"TenderUnderstandingAgent structured output failed: {result.get('parsing_error')}"
            )
        return parsed

    async def arun(self, context: dict) -> TenderSchema:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.tender_understanding"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage_gemini(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_gemini_pro(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.gemini_pro,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(
                f"TenderUnderstandingAgent structured output failed: {result.get('parsing_error')}"
            )
        return parsed
