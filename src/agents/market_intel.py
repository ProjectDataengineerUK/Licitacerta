from __future__ import annotations

import contextlib
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents._gemini_utils import _calc_cost_gemini_flash, _extract_usage_gemini
from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.market import CompetitiveContext
from src.schemas.results import AgentMetric

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter
    from src.services.market_intel_service import MarketIntelService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é o Agente de Inteligência Competitiva do LicitaCerta AI.
Sintetize os dados de mercado em um contexto competitivo claro e acionável.

## Entrada
- `top_competitors`: perfis dos principais concorrentes (CNPJ, taxa de vitória, preço médio)
- `price_benchmark`: benchmark de preço do item (média, min, max, p25, p75)
- `organ_score`: score de adimplência do órgão comprador (0-100, label)
- `segmento_cnae`: código CNAE do segmento

## Sua missão
Preencha o campo `resumo` com 2-3 frases diretas sobre:
1. Nível de concentração do mercado (quem domina?)
2. Referência de preço (onde estamos em relação ao benchmark?)
3. Risco do órgão pagador (paga rápido? inadimplente?)

Se `data_insuficiente=True` em todos os dados, diga isso claramente em `resumo`.

Responda EXCLUSIVAMENTE no schema JSON fornecido."""


class MarketIntelAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.CLASSIFY).with_structured_output(
            CompetitiveContext, include_raw=True
        )
        self._bq: BigQueryWriter | None = None
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()

    def _set_last_metric(
        self, *, tokens_in: int, tokens_out: int, cost_brl: float, latency_ms: int, model_id: str
    ) -> None:
        with self._metric_lock:
            self._last_metric = AgentMetric(
                subgraph="decision",
                agent="market_intel",
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

    def _otel_span(self, name: str):
        try:
            from opentelemetry import trace
            return trace.get_tracer("licitacerta.agents").start_as_current_span(name)
        except Exception:
            return contextlib.nullcontext()

    def _log_bq(self, run_id: str, tenant_id: str, tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        bq = self._get_bq()
        if bq is None:
            return
        try:
            bq.insert_agent_run(
                run_id=run_id,
                tenant_id=tenant_id,
                agent_name="market_intel",
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

    def _build_messages(self, context: dict) -> list:
        lines = [
            f"segmento_cnae: {context.get('segmento_cnae')}",
            f"top_competitors: {context.get('top_competitors')}",
            f"price_benchmark: {context.get('price_benchmark')}",
            f"organ_score: {context.get('organ_score')}",
        ]
        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines)),
        ]

    async def arun(self, context: dict) -> CompetitiveContext:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")

        service: MarketIntelService | None = context.get("service")
        cnpj = context.get("company_cnpj", "")
        segmento_cnae = context.get("segmento_cnae")
        item = context.get("item_descricao", "")
        catmat_code = context.get("catmat_code")
        orgao_cnpj = context.get("orgao_cnpj")
        uasg = context.get("uasg")

        competitors = []
        benchmark = None
        organ = None

        if service:
            try:
                if cnpj:
                    competitors = [await service.competitor_xray(cnpj)]
                if segmento_cnae:
                    summary = await service.segment_summary(segmento_cnae)
                    for top in summary.get("top_fornecedores", [])[:3]:
                        if top["cnpj"] != cnpj:
                            competitors.append(
                                await service.competitor_xray(top["cnpj"])
                            )
            except Exception as exc:
                logger.warning("competitor_xray failed: %s", exc)

            try:
                if item or catmat_code:
                    benchmark = await service.price_benchmark(item, catmat_code, orgao_cnpj)
            except Exception as exc:
                logger.warning("price_benchmark failed: %s", exc)

            try:
                if uasg or orgao_cnpj:
                    organ = await service.organ_score(uasg, orgao_cnpj)
            except Exception as exc:
                logger.warning("organ_score failed: %s", exc)

        # Perfil sem vitória nem preço médio não é sinal de mercado (AT-005)
        has_competitor_signal = any(
            c.total_vitorias > 0 or c.preco_medio_brl is not None for c in competitors
        )
        all_insuficiente = (
            not has_competitor_signal
            and (benchmark is None or benchmark.data_insuficiente)
            and (organ is None or organ.data_insuficiente)
        )

        if all_insuficiente:
            return CompetitiveContext(
                segmento_cnae=segmento_cnae,
                data_insuficiente=True,
                resumo="Dados de mercado insuficientes para análise competitiva neste segmento.",
            )

        messages = self._build_messages({
            "segmento_cnae": segmento_cnae,
            "top_competitors": [c.model_dump() for c in competitors],
            "price_benchmark": benchmark.model_dump() if benchmark else None,
            "organ_score": organ.model_dump() if organ else None,
        })
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.market_intel"):
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

        parsed: CompetitiveContext | None = result.get("parsed")
        if parsed is None:
            logger.warning("MarketIntelAgent structured output failed — usando dados brutos")
            summary_text = context.get("summary_fallback", "")
            cnpj_dom = None
            concentracao = False
            if segmento_cnae and service:
                try:
                    s = await service.segment_summary(segmento_cnae)
                    concentracao = s.get("concentracao_alta", False)
                    cnpj_dom = s.get("cnpj_dominante")
                except Exception:
                    pass
            return CompetitiveContext(
                segmento_cnae=segmento_cnae,
                top_competitors=competitors,
                price_benchmark=benchmark,
                organ_score=organ,
                concentracao_alta=concentracao,
                cnpj_dominante=cnpj_dom,
                resumo=summary_text or "Análise competitiva não disponível.",
            )

        parsed.top_competitors = competitors
        parsed.price_benchmark = benchmark
        parsed.organ_score = organ
        return parsed
