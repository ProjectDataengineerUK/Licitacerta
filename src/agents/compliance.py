from __future__ import annotations

import contextlib
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.model_router import ModelTier, get_llm
from src.config import settings
from src.observability import get_langfuse_handler
from src.schemas.results import AgentMetric, ComplianceResult

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

SYSTEM_PROMPT = """Você é um especialista em licitações públicas brasileiras com profundo conhecimento da \
Lei 14.133/2021, Lei 13.303/2016 e jurisprudência do TCU.

## Sua missão
Analisar o edital estruturado e identificar cláusulas restritivas, ilegais ou que violem princípios \
licitatórios — especialmente aquelas que impedem ou dificultam a participação de PMEs.

## Categorias de cláusulas restritivas

| Categoria | Descrição |
|-----------|-----------|
| ESPECIFICACAO_MARCA | Exigência de fabricante, marca ou modelo específico (Art. 41, §1º, Lei 14.133) |
| HABILITACAO_EXCESSIVA | Certidões, atestados ou qualificações além do mínimo necessário (Súmula TCU 269) |
| PRAZO_INEXEQUIVEL | Prazo de entrega ou execução incompatível com a realidade do mercado |
| GARANTIA_DESPROPORCIONAL | Percentual de garantia acima do máximo legal (5% regra, 10% exceção) |
| CRITERIO_SUBJETIVO | Critério de julgamento que permite arbítrio da Administração |
| RESTRICAO_PORTE | Exigência que elimina ME/EPP sem justificativa técnica (LC 123/2006) |

## Precedentes TCU obrigatórios

Citar sempre que detectar a categoria correspondente:
- **ESPECIFICACAO_MARCA** → Acórdão 2.500/2015-Plenário (vedação a especificações que direcionem para marca)
- **HABILITACAO_EXCESSIVA** → Acórdão 1.284/2023-Plenário (atestados desproporcionais); Súmula TCU 269
- **GARANTIA_DESPROPORCIONAL** → Acórdão 936/2011-Plenário (garantia contratual excessiva)
- **PRAZO_INEXEQUIVEL** → Acórdão 2.696/2022-Plenário (prazo de entrega inexequível)
- **HABILITACAO_EXCESSIVA (técnica)** → Acórdão 1.510/2021-Plenário (habilitação técnica restritiva)
- **CRITERIO_SUBJETIVO** → Acórdão 3.243/2020-Plenário (critérios de julgamento subjetivos)
- **RESTRICAO_PORTE** → Acórdão 1.284/2023-Plenário + LC 123/2006 Art. 48

## Processo de análise (chain-of-thought)

Analise CADA campo do edital estruturado sistematicamente, nesta ordem:

1. **objeto** — escopo é claro e não direciona para solução específica?
2. **modalidade** — modalidade correta para o valor estimado?
3. **exigencias_tecnicas** — há especificações de marca, modelo ou fabricante?
4. **documentos_exigidos** — certidões exigidas têm base legal explícita?
5. **garantia_exigida / garantia_percentual** — dentro dos limites legais (≤5% regra, ≤10% exceção)?
6. **criterio_julgamento** — critério é objetivo e previsível?
7. **prazo_entrega_dias** — compatível com lead time do mercado?
8. **valor_estimado** — exigências proporcionais ao valor?

Apenas após analisar todos os campos, emita o risk_level final.

## Escala de risco — calibração obrigatória

Use EXATAMENTE os critérios abaixo. Não eleve o nível sem a condição específica estar presente.

- **critical**: exigência SEM QUALQUER base legal (ex: certidão emitida por entidade privada sem \
  previsão em lei; declarações que a lei não autoriza); participação tornaria a empresa automaticamente \
  inabilitada se não cumprir; nulidade de pleno direito. Use apenas quando a ilegalidade for flagrante \
  e sem exceção possível.

- **high**: cláusula restritiva com precedente TCU contrário MAS que PODERIA ter justificativa técnica \
  (ex: especificação de marca/modelo quando há equivalentes no mercado; garantia acima do limite legal; \
  prazo de entrega inexequível). Há risco real de impugnação mas a Administração PODERIA alegar \
  justificativa. NÃO eleve para critical se houver qualquer justificativa técnica plausível.

- **medium**: cláusula questionável mas sem precedente TCU direto; risco moderado de impugnação.

- **low**: edital dentro dos padrões legais; pequenas ressalvas que não bloqueiam participação. \
  Um edital com documentos habituais (CNPJ, CND Federal, FGTS), sem exigências técnicas especiais \
  e com penalidades proporcionais é SEMPRE low, mesmo que você identifique pontos de atenção menores.

**Regra de desempate**: na dúvida entre dois níveis adjacentes, escolha o MENOR.

Se risk_level for "critical" ou "high", `human_decision_required` DEVE ser True."""


def _calc_cost_brl(tokens_in: int, tokens_out: int) -> float:
    # Claude Sonnet: $3/M input, $15/M output; USD→BRL @ 5.70
    return (tokens_in * 3 + tokens_out * 15) / 1_000_000 * 5.70


def _extract_usage(raw_message: Any) -> tuple[int, int]:
    try:
        usage = raw_message.response_metadata.get("usage", {})
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    except Exception:
        return 0, 0


class ComplianceAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.LEGAL).with_structured_output(
            ComplianceResult, include_raw=True
        )
        self._bq: BigQueryWriter | None = None
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()
        self._rag_tool: Any = None

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
                agent="compliance",
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

    def _get_rag_tool(self) -> Any:
        if self._rag_tool is None:
            try:
                from src.tools.juridical_search import JuridicalSearchTool
                self._rag_tool = JuridicalSearchTool.from_env()
            except Exception:
                from src.tools.juridical_search import _NoOpJuridicalSearchTool
                self._rag_tool = _NoOpJuridicalSearchTool()
        return self._rag_tool

    def _query_from_context(self, context: dict, content: str) -> str:
        from src.schemas.tender import TenderSchema
        tender = context.get("tender_schema")
        parts: list[str] = []
        if isinstance(tender, TenderSchema):
            if tender.objeto:
                parts.append(tender.objeto[:200])
            if tender.exigencias_tecnicas:
                parts.append(" ".join(tender.exigencias_tecnicas[:3]))
        return " ".join(parts) or content[:300]

    def _build_messages(self, context: dict) -> tuple[list, bool]:
        from src.schemas.tender import TenderSchema
        tender = context.get("tender_schema")
        content = tender.model_dump_json(indent=2) if isinstance(tender, TenderSchema) else str(context)
        query = self._query_from_context(context, content)
        try:
            chunks = self._get_rag_tool().search(query, top_k=5)
        except Exception:
            chunks = []
        return self._assemble_messages(content, chunks), bool(chunks)

    async def _abuild_messages(self, context: dict) -> tuple[list, bool]:
        from src.schemas.tender import TenderSchema
        tender = context.get("tender_schema")
        content = tender.model_dump_json(indent=2) if isinstance(tender, TenderSchema) else str(context)
        query = self._query_from_context(context, content)
        try:
            chunks = await self._get_rag_tool().asearch(query, top_k=5)
        except Exception:
            chunks = []
        return self._assemble_messages(content, chunks), bool(chunks)

    @staticmethod
    def _assemble_messages(content: str, chunks: list) -> list:
        messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
        if chunks:
            rag_block = "## Jurisprudência relevante recuperada da base\n\n" + "\n\n".join(
                f"**{c.tipo.upper()} {c.numero} ({c.fonte})**\n{c.texto}"
                for c in chunks
            )
            messages.append(HumanMessage(content=rag_block))
        messages.append(HumanMessage(content=f"Analise o seguinte edital estruturado:\n\n{content}"))
        return messages

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
                agent_name="compliance",
                model_id=settings.model_sonnet,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_brl(tokens_in, tokens_out),
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

    def run(self, context: dict) -> ComplianceResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages, juridical_context_used = self._build_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.compliance"):
            result = self._llm.invoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_brl(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.model_sonnet,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ComplianceAgent structured output failed: {result.get('parsing_error')}")
        parsed.juridical_context_used = juridical_context_used
        return parsed

    async def arun(self, context: dict) -> ComplianceResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        messages, juridical_context_used = await self._abuild_messages(context)
        callbacks = self._get_callbacks(run_id)
        invoke_config = {"callbacks": callbacks} if callbacks else {}

        t0 = time.time()
        with self._otel_span("agent.compliance"):
            result = await self._llm.ainvoke(messages, config=invoke_config)
        latency_ms = int((time.time() - t0) * 1000)

        tokens_in, tokens_out = _extract_usage(result.get("raw"))
        self._log_bq(run_id, tenant_id, tokens_in, tokens_out, latency_ms)
        self._set_last_metric(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_brl=_calc_cost_brl(tokens_in, tokens_out),
            latency_ms=latency_ms,
            model_id=settings.model_sonnet,
        )

        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ComplianceAgent structured output failed: {result.get('parsing_error')}")
        parsed.juridical_context_used = juridical_context_used
        return parsed
