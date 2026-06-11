from __future__ import annotations

import os
from typing import Literal

import httpx
from pydantic import BaseModel

RECEITAWS_BASE = os.getenv("RECEITAWS_BASE_URL", "https://www.receitaws.com.br/v1/cnpj")


class CnpjLookupResponse(BaseModel):
    razao_social: str | None
    cnae_principal: str | None
    porte: str | None
    municipio: str | None
    source: Literal["receita_federal", "fallback"]


async def cnpj_lookup(cnpj: str) -> CnpjLookupResponse:
    clean = "".join(c for c in cnpj if c.isdigit())
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{RECEITAWS_BASE}/{clean}")
            resp.raise_for_status()
            data = resp.json()
        return CnpjLookupResponse(
            razao_social=data.get("nome"),
            cnae_principal=data.get("cnae_fiscal_descricao"),
            porte=data.get("porte"),
            municipio=data.get("municipio"),
            source="receita_federal",
        )
    except Exception:
        return CnpjLookupResponse(
            razao_social=None,
            cnae_principal=None,
            porte=None,
            municipio=None,
            source="fallback",
        )


async def get_status(tenant_id: str, pool) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM onboarding_ativacao WHERE tenant_id=$1", tenant_id
        )
        ativado = await conn.fetchval(
            "SELECT ativado FROM tenants WHERE id=$1", tenant_id
        )
    if not row:
        return {
            "tenant_id": tenant_id,
            "step_atual": 0,
            "cnpj_preenchido": False,
            "primeiro_edital_submetido": False,
            "analise_concluida": False,
            "email_enviado": False,
            "ativado": bool(ativado),
            "iniciado_em": None,
            "concluido_em": None,
        }
    return {**dict(row), "ativado": bool(ativado)}


_ALLOWED_FLAGS = frozenset(
    {"cnpj_preenchido", "primeiro_edital_submetido", "analise_concluida", "email_enviado", "run_id_express"}
)


async def update_step(tenant_id: str, step: int, flags: dict, pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO onboarding_ativacao (tenant_id, step_atual, iniciado_em, updated_at)
               VALUES ($1, $2, NOW(), NOW())
               ON CONFLICT (tenant_id) DO UPDATE SET
                   step_atual = GREATEST(onboarding_ativacao.step_atual, EXCLUDED.step_atual),
                   updated_at = NOW()""",
            tenant_id,
            step,
        )
        for flag, val in flags.items():
            if flag in _ALLOWED_FLAGS:
                await conn.execute(
                    f"UPDATE onboarding_ativacao SET {flag}=$1, updated_at=NOW() WHERE tenant_id=$2",
                    val,
                    tenant_id,
                )


async def concluir(tenant_id: str, pool, notifications=None) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE onboarding_ativacao
               SET analise_concluida=TRUE, concluido_em=NOW(), updated_at=NOW()
               WHERE tenant_id=$1""",
            tenant_id,
        )
        await conn.execute(
            "UPDATE tenants SET ativado=TRUE WHERE id=$1", tenant_id
        )
    if notifications:
        try:
            await notifications.dispatch_ativacao(tenant_id)
        except Exception:
            pass
