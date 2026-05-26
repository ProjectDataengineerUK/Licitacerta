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
from src.schemas.results import AgentMetric, EligibilityResult

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é o Agente de Elegibilidade do LicitaCerta AI, especializado em \
verificar se uma empresa pode participar de licitações públicas brasileiras com base nos \
requisitos do edital e na Lei 14.133/2021.

## Sua missão
Analisar os requisitos do edital e avaliar a viabilidade de participação de uma PME típica. \
Na ausência de documentos reais da empresa, opere em modo "viabilidade teórica" — avalie se \
uma empresa de pequeno porte conseguiria cumprir os requisitos dentro do prazo normal.

## Categorias de habilitação (Lei 14.133/2021)

### Art. 66 — Habilitação Jurídica
Documentos: CNPJ ativo, ato constitutivo (contrato social ou estatuto), documentos dos \
administradores. Exigência básica para qualquer licitante.

### Art. 67 — Qualificação Técnica
- Registro profissional em entidade competente (CREA, CRM, OAB, etc.)
- Atestados de capacidade técnica operacional
- Acervo técnico do responsável técnico (RT)
- Equipe técnica com formação específica
⚠ Atenção: exigências técnicas desproporcionais ao objeto são ilegais (ver Compliance)

### Art. 68 — Regularidade Fiscal e Trabalhista
Certidões: CND Federal (RFB + PGFN), CND Estadual, CND Municipal, FGTS (CEF), \
CNDT (Justiça do Trabalho). Prazo de validade: 60-90 dias.

### Art. 69 — Qualificação Econômico-Financeira
- Balanço patrimonial do último exercício
- Índices contábeis (Liquidez Corrente, Solvência Geral)
- Capital social mínimo (máximo: 10% do valor do contrato, art. 69 §1º)
- Garantia de proposta (máximo: 1% do valor estimado)

## Análise sistemática

Para cada campo do edital, avalie:
1. `documentos_exigidos` — algum documento é atípico ou sem base legal?
2. `exigencias_tecnicas` — exigência está dentro das capacidades de uma PME do setor?
3. `garantia_exigida`/`garantia_percentual` — está dentro dos limites legais?
4. `prazo_entrega_dias` — tempo razoável para o objeto?

## Campos de saída

- `is_eligible`: true se PME típica conseguiria cumprir todos os requisitos
- `missing_documents`: apenas documentos que exigem prazo para obtenção (certidões, atestados)
- `expiring_certifications`: certidões com validade curta que precisam de atenção (CND, FGTS, CNDT)
- `blocking_issues`: issues com severity="blocking" impedem participação sem impugnação
- `confidence`: 0.0 a 1.0 — menor se edital for ambíguo nos requisitos
- `human_decision_required`: true se houver exigência técnica ambígua ou sem base legal clara

Responda EXCLUSIVAMENTE no schema JSON fornecido."""



class EligibilityAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.CLASSIFY).with_structured_output(
            EligibilityResult, include_raw=True
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
                subgraph="validation",
                agent="eligibility",
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
        from src.schemas.tender import TenderSchema
        tender = context.get("tender_schema")
        cnpj = context.get("company_cnpj", "não informado")
        tender_str = tender.model_dump_json(indent=2) if isinstance(tender, TenderSchema) else str(tender)
        content = f"CNPJ da empresa: {cnpj}\n\nEdital estruturado:\n{tender_str}"
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
                agent_name="eligibility",
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

    def run(self, context: dict) -> EligibilityResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.eligibility"):
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
            raise ValueError(f"EligibilityAgent structured output failed: {result.get('parsing_error')}")
        return parsed

    async def arun(self, context: dict) -> EligibilityResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.eligibility"):
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
            raise ValueError(f"EligibilityAgent structured output failed: {result.get('parsing_error')}")
        return parsed
