"""Worker diário: ingere contratos vencedores do PNCP em market_contracts / market_items."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date, timedelta

import asyncpg

from src.api.pncp_client import PNCPClient

logger = logging.getLogger(__name__)

# CPF regex para redação LGPD antes do UPSERT
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def _strip_pii(raw: dict) -> dict:
    """Remove campos pessoais antes de persistir raw_data."""
    sensitive = {"cpf", "responsavel", "nomResponsavel", "cpfResponsavel"}
    return {k: v for k, v in raw.items() if k not in sensitive}


async def _upsert_contract(conn: asyncpg.Connection, c: dict) -> None:
    numero_controle = c.get("numeroControlePNCP") or c.get("numeroControle", "")
    if not numero_controle:
        return

    data_str = c.get("dataAssinatura") or c.get("dataContrato") or date.today().isoformat()
    try:
        data_contrato = date.fromisoformat(data_str[:10])
    except Exception:
        data_contrato = date.today()

    raw_clean = _strip_pii(c)
    # também aplica máscara em string raw
    import json
    raw_json = _CPF_RE.sub("***CPF***", json.dumps(raw_clean, ensure_ascii=False))

    await conn.execute(
        """
        INSERT INTO market_contracts (
            numero_controle, orgao_cnpj, orgao_nome, uasg,
            fornecedor_cnpj, fornecedor_nome,
            objeto, segmento_cnae, modalidade, valor_global,
            data_contrato, data_adjudicacao, prazo_pagamento_dias, raw_data
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb)
        ON CONFLICT (numero_controle, data_contrato) DO UPDATE
            SET orgao_nome      = EXCLUDED.orgao_nome,
                fornecedor_nome = EXCLUDED.fornecedor_nome,
                valor_global    = EXCLUDED.valor_global,
                raw_data        = EXCLUDED.raw_data
        """,
        numero_controle,
        c.get("orgaoEntidade", {}).get("cnpj", ""),
        c.get("orgaoEntidade", {}).get("razaoSocial"),
        c.get("unidadeOrgao", {}).get("codigoUnidade"),
        c.get("fornecedor", {}).get("cnpj", "") or c.get("fornecedorCnpj", ""),
        c.get("fornecedor", {}).get("nome") or c.get("fornecedorNome"),
        c.get("objetoContrato") or c.get("objeto"),
        c.get("codigoCategoriaCNAE") or c.get("segmentoCNAE"),
        c.get("codigoModalidadeContratacao"),
        c.get("valorGlobal") or c.get("valorInicial"),
        data_contrato,
        date.fromisoformat(c["dataAdjudicacao"][:10]) if c.get("dataAdjudicacao") else None,
        c.get("prazoPagamento") or c.get("prazoPagamentoDias"),
        raw_json,
    )


async def run_market_intel_ingest(days_back: int = 1) -> None:
    db_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(db_url)
    try:
        data_final = date.today()
        data_inicial = data_final - timedelta(days=days_back)

        logger.info("Ingerindo contratos PNCP %s → %s", data_inicial, data_final)

        async with PNCPClient() as client:
            contratos = await client.fetch_contratos(data_inicial, data_final)

        logger.info("Contratos recebidos: %d", len(contratos))

        async with conn.transaction():
            for c in contratos:
                try:
                    await _upsert_contract(conn, c)
                except Exception as exc:
                    logger.warning("UPSERT falhou para %s: %s", c.get("numeroControlePNCP"), exc)

        logger.info("Ingestão concluída.")
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(run_market_intel_ingest(days))
