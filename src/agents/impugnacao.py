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
from src.schemas.results import AgentMetric, ImpugnacaoAction, ImpugnacaoResult

if TYPE_CHECKING:
    from src.gcp.bigquery import BigQueryWriter

logger = logging.getLogger(__name__)

# Pricing: Claude Sonnet — same as compliance (ModelTier.LEGAL)
_COST_INPUT_PER_TOKEN = 3.0 / 1_000_000   # USD
_COST_OUTPUT_PER_TOKEN = 15.0 / 1_000_000  # USD
_USD_TO_BRL = 5.0


def _calc_cost_brl(tokens_in: int, tokens_out: int) -> float:
    usd = tokens_in * _COST_INPUT_PER_TOKEN + tokens_out * _COST_OUTPUT_PER_TOKEN
    return round(usd * _USD_TO_BRL, 6)


def _extract_usage(raw: Any) -> tuple[int, int]:
    try:
        usage = raw.response_metadata.get("usage", {})
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)
    except Exception:
        return 0, 0


SYSTEM_PROMPT = """Você é o Agente de Impugnação do LicitaCerta AI, especializado em direito licitatório \
brasileiro. Sua função é analisar cláusulas restritivas identificadas no edital e gerar ações de \
impugnação ou pedido de esclarecimento conforme a Lei 14.133/2021.

## Competências

- **Impugnação (Art. 164, Lei 14.133/2021):** cabível quando a cláusula é ilegal, viola a isonomia ou \
impede a participação de licitantes em condições de executar o objeto.
- **Pedido de esclarecimento (Art. 164, §1º):** cabível quando a cláusula é ambígua, contraditória ou \
carece de fundamentação — mas pode ter interpretação válida.

## Prazo legal
O prazo para apresentação de impugnações e pedidos de esclarecimento é de até 3 (três) dias úteis \
antes da data de abertura das propostas (Art. 164, caput, Lei 14.133/2021).

## Para cada cláusula restritiva, gere:
1. **tipo:** "impugnar" (cláusula ilegal) ou "pedir_esclarecimento" (cláusula ambígua)
2. **clause_description:** descrição objetiva da cláusula problemática
3. **fundamento_legal:** artigo(s) da Lei 14.133/2021, jurisprudência TCU ou LC 123/2006 aplicáveis
4. **minuta:** texto da impugnação ou pedido de esclarecimento, com identificação do edital, \
fundamentação jurídica, pedido e encerramento formal

## Padrão de minuta
A minuta deve:
- Identificar o instrumento convocatório (número, órgão)
- Citar o trecho exato da cláusula questionada
- Apresentar o fundamento legal e jurisprudencial
- Formular pedido claro (anulação da cláusula, esclarecimento, adequação)
- Usar linguagem técnica e formal

## Resposta estruturada
Retorne uma lista de ImpugnacaoAction para cada cláusula restritiva identificada.
"""

_ACTION_SCHEMA_PROMPT = """Analise a seguinte cláusula restritiva e gere a ação correspondente.

**Edital:** {edital_info}
**Cláusula:** {clause_description}
**Severidade:** {severity}
**Categoria TCU:** {tcu_category}

Gere a ação de impugnação ou pedido de esclarecimento em JSON com os campos:
- tipo: "impugnar" ou "pedir_esclarecimento"
- clause_description: descrição objetiva da cláusula
- fundamento_legal: fundamento legal aplicável
- minuta: texto formal completo da impugnação/esclarecimento
"""


class ImpugnacaoAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.LEGAL).with_structured_output(
            ImpugnacaoAction, include_raw=True
        )
        self._bq: BigQueryWriter | None = None
        self._last_metric: AgentMetric | None = None
        self._metric_lock = threading.Lock()

    def _set_last_metric(self, *, tokens_in: int, tokens_out: int, cost_brl: float, latency_ms: int) -> None:
        with self._metric_lock:
            self._last_metric = AgentMetric(
                subgraph="validation",
                agent="impugnacao",
                metric_name="cost_brl",
                value=cost_brl,
                timestamp=datetime.utcnow(),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_brl=cost_brl,
                latency_ms=latency_ms,
                model_id=settings.model_sonnet,
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

    def _get_callbacks(self, run_id: str) -> list:
        try:
            handler = get_langfuse_handler(run_id)
            return [handler] if handler else []
        except Exception:
            return []

    def _log_bq(self, run_id: str, tenant_id: str, tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        bq = self._get_bq()
        if bq is None:
            return
        try:
            bq.insert_agent_run(
                run_id=run_id,
                tenant_id=tenant_id,
                agent_name="impugnacao",
                model_id=settings.model_sonnet,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                cost_brl=_calc_cost_brl(tokens_in, tokens_out),
                eval_score=None,
            )
        except Exception:
            pass

    @staticmethod
    def _extract_high_critical(compliance_result: Any) -> list:
        try:
            return [
                issue for issue in compliance_result.restrictive_clauses
                if hasattr(issue, "severity") and issue.severity in ("high", "blocking")
            ]
        except Exception:
            return []

    @staticmethod
    def _consolidate_recommendation(actions: list[ImpugnacaoAction]) -> str:
        valid_actions = [a for a in actions if a.valido]
        if not valid_actions:
            return "nao_participar" if actions else "participar"
        if any(a.tipo == "impugnar" for a in valid_actions):
            return "impugnar"
        return "pedir_esclarecimento"

    @staticmethod
    def _calc_prazo(tender_schema: Any) -> Any:
        try:
            from src.utils.business_days import subtract_business_days
            opening_date = tender_schema.data_abertura
            if opening_date is None:
                return None
            prazo = subtract_business_days(opening_date, 3)
            return prazo
        except Exception:
            return None

    def _build_action_messages(self, edital_info: str, issue: Any) -> list:
        clause_desc = getattr(issue, "description", str(issue))
        severity = getattr(issue, "severity", "high")
        tcu_category = ""
        if hasattr(issue, "evidence") and issue.evidence:
            tcu_category = str(issue.evidence)
        prompt = _ACTION_SCHEMA_PROMPT.format(
            edital_info=edital_info,
            clause_description=clause_desc,
            severity=severity,
            tcu_category=tcu_category,
        )
        return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]

    def _run_action(
        self, edital_info: str, issue: Any, prazo_limite: Any, callbacks: list
    ) -> tuple[ImpugnacaoAction, int, int]:
        messages = self._build_action_messages(edital_info, issue)
        invoke_config = {"callbacks": callbacks} if callbacks else {}
        result = self._llm.invoke(messages, config=invoke_config)
        tokens_in, tokens_out = _extract_usage(result.get("raw"))
        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ImpugnacaoAgent structured output failed: {result.get('parsing_error')}")
        from datetime import date
        parsed.prazo_limite = prazo_limite
        parsed.valido = prazo_limite is None or prazo_limite >= date.today()
        return parsed, tokens_in, tokens_out

    async def _arun_action(
        self, edital_info: str, issue: Any, prazo_limite: Any, callbacks: list
    ) -> tuple[ImpugnacaoAction, int, int]:
        messages = self._build_action_messages(edital_info, issue)
        invoke_config = {"callbacks": callbacks} if callbacks else {}
        result = await self._llm.ainvoke(messages, config=invoke_config)
        tokens_in, tokens_out = _extract_usage(result.get("raw"))
        parsed = result.get("parsed")
        if parsed is None:
            raise ValueError(f"ImpugnacaoAgent structured output failed: {result.get('parsing_error')}")
        from datetime import date
        parsed.prazo_limite = prazo_limite
        parsed.valido = prazo_limite is None or prazo_limite >= date.today()
        return parsed, tokens_in, tokens_out

    def run(self, context: dict) -> ImpugnacaoResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        compliance_result = context.get("compliance_result")
        tender_schema = context.get("tender_schema")

        high_critical = self._extract_high_critical(compliance_result)

        # LLM skip: zero cost when no high/critical clauses
        if not high_critical:
            return ImpugnacaoResult(
                conclusion="Nenhuma cláusula de alto risco ou crítica identificada. Participação recomendada.",
                confidence=1.0,
                recommended_action="participar",
                recommendation="participar",
                human_decision_required=False,
            )

        prazo_limite = self._calc_prazo(tender_schema)
        edital_info = (
            f"{getattr(tender_schema, 'orgao', '')} — {getattr(tender_schema, 'objeto', '')}"
            if tender_schema else "Edital não informado"
        )

        callbacks = self._get_callbacks(run_id)
        actions: list[ImpugnacaoAction] = []
        total_in = total_out = 0

        t0 = time.time()
        with self._otel_span("agent.impugnacao"):
            for issue in high_critical:
                try:
                    action, tin, tout = self._run_action(edital_info, issue, prazo_limite, callbacks)
                    actions.append(action)
                    total_in += tin
                    total_out += tout
                except Exception as exc:
                    logger.warning("ImpugnacaoAgent: failed to generate action for clause: %s", exc)
        latency_ms = int((time.time() - t0) * 1000)

        self._log_bq(run_id, tenant_id, total_in, total_out, latency_ms)
        self._set_last_metric(
            tokens_in=total_in,
            tokens_out=total_out,
            cost_brl=_calc_cost_brl(total_in, total_out),
            latency_ms=latency_ms,
        )

        recommendation = self._consolidate_recommendation(actions)
        human_required = recommendation in ("impugnar", "nao_participar")
        n_invalid = sum(1 for a in actions if not a.valido)
        conclusion = (
            f"Identificadas {len(high_critical)} cláusula(s) de alto risco/críticas. "
            f"Geradas {len(actions)} ação(ões). "
            f"Prazo expirado para {n_invalid} ação(ões)."
        )

        return ImpugnacaoResult(
            conclusion=conclusion,
            confidence=0.9,
            recommended_action=recommendation,
            recommendation=recommendation,
            actions=actions,
            prazo_limite=prazo_limite,
            human_decision_required=human_required,
        )

    async def arun(self, context: dict) -> ImpugnacaoResult:
        run_id = context.get("run_id") or str(uuid.uuid4())
        tenant_id = context.get("tenant_id", "unknown")
        compliance_result = context.get("compliance_result")
        tender_schema = context.get("tender_schema")

        high_critical = self._extract_high_critical(compliance_result)

        if not high_critical:
            return ImpugnacaoResult(
                conclusion="Nenhuma cláusula de alto risco ou crítica identificada. Participação recomendada.",
                confidence=1.0,
                recommended_action="participar",
                recommendation="participar",
                human_decision_required=False,
            )

        prazo_limite = self._calc_prazo(tender_schema)
        edital_info = (
            f"{getattr(tender_schema, 'orgao', '')} — {getattr(tender_schema, 'objeto', '')}"
            if tender_schema else "Edital não informado"
        )

        callbacks = self._get_callbacks(run_id)
        actions: list[ImpugnacaoAction] = []
        total_in = total_out = 0

        t0 = time.time()
        with self._otel_span("agent.impugnacao"):
            for issue in high_critical:
                try:
                    action, tin, tout = await self._arun_action(edital_info, issue, prazo_limite, callbacks)
                    actions.append(action)
                    total_in += tin
                    total_out += tout
                except Exception as exc:
                    logger.warning("ImpugnacaoAgent: failed to generate action for clause: %s", exc)
        latency_ms = int((time.time() - t0) * 1000)

        self._log_bq(run_id, tenant_id, total_in, total_out, latency_ms)
        self._set_last_metric(
            tokens_in=total_in,
            tokens_out=total_out,
            cost_brl=_calc_cost_brl(total_in, total_out),
            latency_ms=latency_ms,
        )

        recommendation = self._consolidate_recommendation(actions)
        human_required = recommendation in ("impugnar", "nao_participar")
        n_invalid = sum(1 for a in actions if not a.valido)
        conclusion = (
            f"Identificadas {len(high_critical)} cláusula(s) de alto risco/críticas. "
            f"Geradas {len(actions)} ação(ões). "
            f"Prazo expirado para {n_invalid} ação(ões)."
        )

        return ImpugnacaoResult(
            conclusion=conclusion,
            confidence=0.9,
            recommended_action=recommendation,
            recommendation=recommendation,
            actions=actions,
            prazo_limite=prazo_limite,
            human_decision_required=human_required,
        )
