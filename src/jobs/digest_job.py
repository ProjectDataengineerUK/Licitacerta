"""DIGEST_DIARIO — job batch diário (Cloud Run Job).

Fluxo: carrega tenants ativos → plan-gate → fetch oportunidades (mock PNCP V1)
→ ranking → resumos Gemini Flash → email HTML → log idempotente.

Degradação graciosa: Gemini falha → item sem resumo. Email/tenant falha → loga + segue.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import date

import asyncpg

from src.agents.model_router import ModelTier, get_llm
from src.services.digest_plan import should_send_today
from src.services.email import send_digest_email

logger = logging.getLogger(__name__)

_MAX_CONCURRENCY = int(os.getenv("DIGEST_CONCURRENCY", "8"))
_TOP_N = 5
_RESUMO_MAX_TOKENS = 150
_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@dataclass
class Oportunidade:
    run_id: str
    titulo: str
    orgao: str
    uf: str
    cnae: str
    valor: float
    objeto: str
    score: float = 0.0
    resumo: str | None = None


@dataclass
class TenantConfig:
    tenant_id: str
    email: str
    plan: str
    ufs: list[str]
    cnaes: list[str]
    palavras_chave: list[str]
    valor_min: float | None
    valor_max: float | None
    canal_email: bool
    canal_push: bool = False


async def fetch_oportunidades(cfg: TenantConfig) -> list[Oportunidade]:
    """V1: mock estável. Substituível por PNCPClient.search_publicacoes_all sem mudar assinatura."""
    return [
        Oportunidade(
            run_id=f"mock-{cfg.tenant_id[:6]}-{i}",
            titulo=f"Pregão Eletrônico {i:03d}/2026",
            orgao="Prefeitura Municipal (mock)",
            uf=(cfg.ufs[i % len(cfg.ufs)] if cfg.ufs else "SP"),
            cnae=(cfg.cnaes[i % len(cfg.cnaes)] if cfg.cnaes else "6201-5"),
            valor=50_000.0 * (i + 1),
            objeto="Contratação de serviços de TI e suporte técnico continuado.",
        )
        for i in range(12)
    ]


def rank_oportunidades(ops: list[Oportunidade], cfg: TenantConfig) -> list[Oportunidade]:
    palavras = [p.lower() for p in cfg.palavras_chave]
    for op in ops:
        score = 0.0
        if cfg.ufs and op.uf in cfg.ufs:
            score += 3.0
        if cfg.cnaes and any(op.cnae.startswith(c) for c in cfg.cnaes):
            score += 3.0
        blob = f"{op.titulo} {op.objeto}".lower()
        score += sum(2.0 for p in palavras if p in blob)
        if cfg.valor_min is not None and op.valor < cfg.valor_min:
            score -= 2.0
        if cfg.valor_max is not None and op.valor > cfg.valor_max:
            score -= 2.0
        op.score = score
    ranked = sorted(ops, key=lambda o: o.score, reverse=True)
    return [o for o in ranked if o.score > 0][:_TOP_N] or ranked[:_TOP_N]


async def gerar_resumo(op: Oportunidade) -> str | None:
    try:
        llm = get_llm(ModelTier.CLASSIFY)
        prompt = (
            "Resuma esta oportunidade de licitação para um dono de PME em "
            f"no máximo 2 frases ({_RESUMO_MAX_TOKENS} tokens). "
            "Destaque objeto e atratividade. Sem preâmbulo.\n\n"
            f"Órgão: {op.orgao} | UF: {op.uf} | Valor: R$ {op.valor:,.2f}\n"
            f"Objeto: {op.objeto}"
        )
        resp = await llm.ainvoke([{"role": "user", "content": prompt}])
        content = getattr(resp, "content", None) or str(resp)
        return content.strip()[:600] or None
    except Exception as exc:
        logger.warning("Gemini resumo falhou (run %s): %s", op.run_id, exc)
        return None


async def _enriquecer_resumos(ops: list[Oportunidade]) -> None:
    results = await asyncio.gather(*(gerar_resumo(op) for op in ops), return_exceptions=True)
    for op, res in zip(ops, results):
        op.resumo = res if isinstance(res, str) else None


async def _processar_tenant(
    conn_pool: asyncpg.Pool,
    cfg: TenantConfig,
    digest_date: date,
    sem: asyncio.Semaphore,
) -> None:
    async with sem:
        if not should_send_today(cfg.plan, digest_date.weekday()):
            logger.info("skip tenant=%s plan=%s (gate)", cfg.tenant_id, cfg.plan)
            return

        if not cfg.canal_email:
            return

        ops = await fetch_oportunidades(cfg)
        top = rank_oportunidades(ops, cfg)
        if not top:
            return
        await _enriquecer_resumos(top)

        from src.jobs.digest_template import build_digest_html
        html = build_digest_html(cfg.tenant_id, top, digest_date, _FRONTEND_URL)

        ok = await send_digest_email(
            to=cfg.email,
            html=html,
            subject=f"Suas {len(top)} oportunidades de hoje — LicitaCerta",
        )
        if not ok:
            logger.warning("envio falhou tenant=%s — não registra log", cfg.tenant_id)
            return

        async with conn_pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO digest_log (tenant_id, digest_date, itens_enviados)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (tenant_id, digest_date) DO NOTHING""",
                cfg.tenant_id, digest_date, len(top),
            )
        logger.info("digest enviado tenant=%s itens=%d", cfg.tenant_id, len(top))


async def _load_tenant_configs(pool: asyncpg.Pool) -> list[TenantConfig]:
    rows = await pool.fetch(
        """SELECT c.tenant_id, c.ufs, c.cnaes, c.palavras_chave,
                  c.valor_min, c.valor_max, c.canal_email, c.canal_push,
                  COALESCE(t.email, '')    AS email,
                  COALESCE(t.plan, 'free') AS plan
             FROM digest_config c
             LEFT JOIN tenants t ON t.id = c.tenant_id
            WHERE c.ativo = TRUE"""
    )
    out: list[TenantConfig] = []
    for r in rows:
        if not r["email"]:
            continue
        out.append(TenantConfig(
            tenant_id=r["tenant_id"], email=r["email"], plan=r["plan"],
            ufs=list(r["ufs"] or []), cnaes=list(r["cnaes"] or []),
            palavras_chave=list(r["palavras_chave"] or []),
            valor_min=float(r["valor_min"]) if r["valor_min"] is not None else None,
            valor_max=float(r["valor_max"]) if r["valor_max"] is not None else None,
            canal_email=r["canal_email"], canal_push=r["canal_push"],
        ))
    return out


async def run_digest(digest_date: date | None = None) -> int:
    digest_date = digest_date or date.today()
    db_url = os.environ["DATABASE_URL"]
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=_MAX_CONCURRENCY)
    try:
        configs = await _load_tenant_configs(pool)
        logger.info("digest_date=%s tenants_ativos=%d", digest_date, len(configs))
        sem = asyncio.Semaphore(_MAX_CONCURRENCY)
        await asyncio.gather(
            *(_processar_tenant(pool, c, digest_date, sem) for c in configs),
            return_exceptions=True,
        )
        return len(configs)
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_digest())
