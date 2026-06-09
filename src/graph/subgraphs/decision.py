from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import END, StateGraph

from src.agents.bid_no_bid import BidNoBidAgent
from src.agents.estrategia import EstrategiaAgent
from src.agents.impugnacao import ImpugnacaoAgent
from src.agents.market_intel import MarketIntelAgent
from src.agents.pricing import PricingAgent
from src.config import settings
from src.graph._async_utils import run_in_thread
from src.graph.state import TenderState
from src.schemas.results import AgentError, AuditEvent


def should_impugnar(state: TenderState) -> bool:
    bid = state.get("bid_decision")
    compliance = state.get("compliance")
    if bid is not None and getattr(bid, "recommendation", None) == "impugnar":
        return True
    if bid is not None and getattr(bid, "recommended_action", None) == "impugnar":
        return True
    if compliance is not None and compliance.risk_level == "critical":
        return True
    if compliance is not None and any(
        getattr(i, "severity", None) == "blocking" for i in compliance.blocking_issues
    ):
        return True
    return False


def build_decision_subgraph():
    _market_intel: MarketIntelAgent | None = None
    _pricing: PricingAgent | None = None
    _bid: BidNoBidAgent | None = None
    _estrategia: EstrategiaAgent | None = None
    _impugnacao: ImpugnacaoAgent | None = None

    async def run_market_intel(state: TenderState) -> dict:
        nonlocal _market_intel
        if _market_intel is None:
            _market_intel = MarketIntelAgent()
        t0 = time.time()
        tender = state.get("tender_schema")
        try:
            context = {
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
                "company_cnpj": state.get("company_cnpj", ""),
                "segmento_cnae": getattr(tender, "segmento_cnae", None) if tender else None,
                "item_descricao": getattr(tender, "objeto", "") if tender else "",
                "catmat_code": getattr(tender, "catmat_code", None) if tender else None,
                "orgao_cnpj": getattr(tender, "orgao_cnpj", None) if tender else None,
                "uasg": getattr(tender, "uasg", None) if tender else None,
                "service": None,  # Service injected via DI quando disponível
            }
            result = await _market_intel.arun(context)
            metric = _market_intel.get_last_metric()
            return {
                "competitive_context": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="market_intel",
                        action="analyze_market",
                        input_summary=f"cnpj={state.get('company_cnpj')} segmento={context['segmento_cnae']}",
                        output_summary=f"data_insuficiente={result.data_insuficiente} resumo={result.resumo[:80]}",
                        model_used=settings.gemini_flash,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "competitive_context": None,
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="market_intel",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    async def run_pricing(state: TenderState) -> dict:
        nonlocal _pricing
        if _pricing is None:
            _pricing = PricingAgent()
        t0 = time.time()
        try:
            result = await run_in_thread(_pricing.run, {
                "tender_schema": state.get("tender_schema"),
                "eligibility": state.get("eligibility"),
                "compliance": state.get("compliance"),
                "blacklist": state.get("blacklist"),
                "competitive_context": state.get("competitive_context"),
                "company_cnpj": state["company_cnpj"],
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            metric = _pricing.get_last_metric()
            return {
                "pricing": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="pricing",
                        action="calculate_price",
                        input_summary=f"cnpj={state['company_cnpj']}",
                        output_summary=f"price={result.recommended_price} margin={result.min_margin_pct:.1f}%",
                        model_used=settings.gemini_pro,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="pricing",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    async def run_bid_no_bid(state: TenderState) -> dict:
        nonlocal _bid
        if _bid is None:
            _bid = BidNoBidAgent()
        t0 = time.time()
        try:
            result = await run_in_thread(_bid.run, {
                "tender_schema": state.get("tender_schema"),
                "eligibility": state.get("eligibility"),
                "compliance": state.get("compliance"),
                "blacklist": state.get("blacklist"),
                "pricing": state.get("pricing"),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            metric = _bid.get_last_metric()
            return {
                "bid_decision": result,
                "current_step": "decided",
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="bid_no_bid",
                        action="decide",
                        input_summary=f"edital_id={state['edital_id']}",
                        output_summary=f"recommendation={result.recommendation} risk={result.risk_level}",
                        model_used=settings.gemini_pro,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="bid_no_bid",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
                "current_step": "decided",
            }

    async def run_estrategia(state: TenderState) -> dict:
        nonlocal _estrategia
        if _estrategia is None:
            _estrategia = EstrategiaAgent()
        t0 = time.time()
        try:
            result = await _estrategia.arun({
                "tender_schema": state.get("tender_schema"),
                "bid_decision": state.get("bid_decision"),
                "compliance": state.get("compliance"),
                "pricing": state.get("pricing"),
                "competitive_context": state.get("competitive_context"),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            metric = _estrategia.get_last_metric()
            return {
                "estrategia_result": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="estrategia",
                        action="generate_strategy",
                        input_summary=f"bid={getattr(state.get('bid_decision'), 'recommendation', 'N/A')}",
                        output_summary=f"prob_com_acoes={result.probabilidade_com_acoes_pct:.0f}% acoes={len(result.acoes)}",
                        model_used=settings.gemini_pro,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "estrategia_result": None,
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="estrategia",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    async def run_cashflow(state: TenderState) -> dict:
        t0 = time.time()
        try:
            from decimal import Decimal as _Decimal
            from math import ceil as _ceil
            from src.services.cashflow_simulator import simular

            tender = state.get("tender_schema")
            pricing = state.get("pricing")

            valor_mensal = (
                getattr(pricing, "recommended_price", None)
                or (getattr(tender, "valor_estimado", None) if tender else None)
                or _Decimal(0)
            )
            custo_mensal = (
                getattr(pricing, "cost_estimate", None)
                or valor_mensal * _Decimal("0.8")
            )
            prazo_dias = getattr(tender, "prazo_pagamento_dias", 30) if tender else 30
            duracao = getattr(tender, "duracao_meses", 12) if tender else 12
            caixa_inicial = _Decimal(
                state.get("tenant_caixa_inicial_brl") or 0
            )

            sim = simular(
                valor_mensal_brl=_Decimal(str(valor_mensal)),
                prazo_pagamento_dias=int(prazo_dias or 30),
                custo_mensal_brl=_Decimal(str(custo_mensal)),
                duracao_meses=int(duracao or 12),
                caixa_inicial_brl=caixa_inicial,
            )
            return {
                "cashflow_simulation": sim,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="cashflow",
                        action="simulate",
                        input_summary=f"prazo={prazo_dias}d duracao={duracao}m",
                        output_summary=f"risco={sim.risco} capital={sim.capital_giro_necessario_brl}",
                        model_used="deterministic",
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
            }
        except Exception as e:
            return {
                "cashflow_simulation": None,
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="cashflow",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    async def run_pregoeiro(state: TenderState) -> dict:
        t0 = time.time()
        tender = state.get("tender_schema")
        pregoeiro_nome = getattr(tender, "pregoeiro_nome", None) if tender else None
        if not pregoeiro_nome:
            return {"pregoeiro_perfil": None}
        try:
            import os
            import asyncpg
            from src.services.pregoeiro_service import PregoeicoService
            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                return {"pregoeiro_perfil": None}
            orgao_cnpj = getattr(tender, "orgao_cnpj", "") or ""
            conn = await asyncpg.connect(db_url)
            try:
                svc = PregoeicoService(conn)
                perfil = await svc.lookup(nome=pregoeiro_nome, orgao_cnpj=orgao_cnpj)
            finally:
                await conn.close()
            return {
                "pregoeiro_perfil": perfil,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="pregoeiro",
                        action="lookup_profile",
                        input_summary=f"nome={pregoeiro_nome} orgao={orgao_cnpj}",
                        output_summary=f"sessoes={perfil.total_sessoes} indice={perfil.indice_reputacao}",
                        model_used="deterministic",
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
            }
        except Exception as e:
            return {
                "pregoeiro_perfil": None,
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="pregoeiro",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    async def run_impugnacao(state: TenderState) -> dict:
        nonlocal _impugnacao
        if _impugnacao is None:
            _impugnacao = ImpugnacaoAgent()
        t0 = time.time()
        try:
            result = await _impugnacao.arun({
                "compliance_result": state.get("compliance"),
                "tender_schema": state.get("tender_schema"),
                "run_id": state.get("run_id"),
                "tenant_id": state.get("tenant_id"),
            })
            result.human_decision_required = True
            metric = _impugnacao.get_last_metric()
            return {
                "impugnacao": result,
                "audit_log": [
                    AuditEvent(
                        subgraph="decision",
                        agent="impugnacao",
                        action="generate_actions",
                        input_summary=f"recommendation={result.recommendation} actions={len(result.actions)}",
                        output_summary=result.conclusion,
                        model_used=settings.model_sonnet,
                        latency_ms=int((time.time() - t0) * 1000),
                        tokens_used=0,
                        timestamp=datetime.utcnow(),
                    )
                ],
                "metrics": [metric] if metric else [],
            }
        except Exception as e:
            return {
                "errors": [
                    AgentError(
                        subgraph="decision",
                        agent="impugnacao",
                        error_type=type(e).__name__,
                        message=str(e),
                        timestamp=datetime.utcnow(),
                        recoverable=True,
                    )
                ],
            }

    g: StateGraph = StateGraph(TenderState)
    g.add_node("market_intel", run_market_intel)
    g.add_node("price_calc", run_pricing)
    g.add_node("bid_no_bid", run_bid_no_bid)
    g.add_node("run_estrategia", run_estrategia)
    g.add_node("run_cashflow", run_cashflow)
    g.add_node("run_pregoeiro", run_pregoeiro)
    g.add_node("run_impugnacao", run_impugnacao)
    g.set_entry_point("market_intel")
    g.add_edge("market_intel", "price_calc")
    g.add_edge("price_calc", "bid_no_bid")
    g.add_edge("bid_no_bid", "run_estrategia")
    g.add_edge("run_estrategia", "run_cashflow")
    g.add_edge("run_cashflow", "run_pregoeiro")
    g.add_conditional_edges(
        "run_pregoeiro",
        lambda state: "run_impugnacao" if should_impugnar(state) else END,
        {"run_impugnacao": "run_impugnacao", END: END},
    )
    g.add_edge("run_impugnacao", END)
    return g.compile()
