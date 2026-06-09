"""Weekly Cloud Scheduler job: compute pregoeiro reputation profiles from PNCP."""
from __future__ import annotations

import asyncio
import logging
import unicodedata
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _calc_previsibilidade(tempos: list[float]) -> float:
    if len(tempos) < 2:
        return 0.5
    import statistics
    mean = statistics.mean(tempos)
    if mean == 0:
        return 1.0
    cv = statistics.stdev(tempos) / mean  # coeficiente de variação
    return max(0.0, min(1.0, 1.0 - cv))


def _agregar_por_pregoeiro(sessoes: list[dict], impugnacoes: list[dict]) -> list[dict]:
    grupos: dict[tuple, list] = defaultdict(list)
    for s in sessoes:
        nome = s.get("nomePregoeiro") or s.get("responsavel") or ""
        orgao = s.get("cnpjOrgao") or ""
        if nome and orgao:
            grupos[(nome, orgao)].append(s)

    impugnacoes_por_pregoeiro: dict[tuple, list] = defaultdict(list)
    for imp in impugnacoes:
        nome = imp.get("nomePregoeiro") or ""
        orgao = imp.get("cnpjOrgao") or ""
        if nome and orgao:
            impugnacoes_por_pregoeiro[(nome, orgao)].append(imp)

    perfis: list[dict] = []
    for (nome, orgao), sessoes_list in grupos.items():
        total = len(sessoes_list)
        tempos = [s.get("duracaoHoras") or 0 for s in sessoes_list if s.get("duracaoHoras")]
        tempo_medio = sum(tempos) / len(tempos) if tempos else None
        previsibilidade = _calc_previsibilidade(tempos) if tempos else None

        imps = impugnacoes_por_pregoeiro.get((nome, orgao), [])
        imp_aceitas = sum(1 for i in imps if i.get("deferida"))
        taxa_imp = (imp_aceitas / len(imps) * 100) if imps else None

        desclassificacoes = [s for s in sessoes_list if s.get("temDesclassificacao")]
        taxa_desc = (len(desclassificacoes) / total * 100) if total > 0 else None

        vencedores: dict[str, dict] = defaultdict(lambda: {"cnpj": "", "nome": None, "frequencia": 0})
        for s in sessoes_list:
            cnpj_venc = s.get("cnpjVencedor")
            if cnpj_venc:
                vencedores[cnpj_venc]["cnpj"] = cnpj_venc
                vencedores[cnpj_venc]["nome"] = s.get("nomeVencedor")
                vencedores[cnpj_venc]["frequencia"] += 1

        top_venc = sorted(vencedores.values(), key=lambda x: x["frequencia"], reverse=True)[:5]

        perfis.append({
            "nome": nome,
            "nome_normalizado": _normalize(nome),
            "orgao_cnpj": orgao,
            "orgao_nome": sessoes_list[0].get("nomeOrgao") if sessoes_list else None,
            "total_sessoes": total,
            "taxa_aceitacao_impugnacao_pct": taxa_imp,
            "taxa_desclassificacao_pct": taxa_desc,
            "tempo_medio_sessao_horas": tempo_medio,
            "previsibilidade": previsibilidade,
            "clausulas_frequentes": [],
            "tipos_desclassificacao": [],
            "empresas_frequentes_vencedoras": top_venc,
        })
    return perfis


async def run_pregoeiro_update(db_url: str | None = None) -> None:
    import os
    url = db_url or os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set — aborting pregoeiro worker")
        return

    import asyncpg
    from src.api.pncp_client import PNCPClient

    conn = await asyncpg.connect(url)
    try:
        orgaos = await conn.fetch(
            "SELECT DISTINCT orgao_cnpj FROM market_contracts WHERE data_contrato > NOW() - INTERVAL '90 days' LIMIT 100"
        )
        orgao_cnpjs = [r["orgao_cnpj"] for r in orgaos]
    except Exception as exc:
        logger.warning("pregoeiro_worker: failed to fetch orgaos: %s", exc)
        await conn.close()
        return

    from datetime import date, timedelta
    data_inicio = (date.today() - timedelta(days=90)).isoformat()
    data_fim = date.today().isoformat()

    async with PNCPClient() as client:
        for orgao_cnpj in orgao_cnpjs[:20]:  # rate-limit: 20 orgaos/run
            try:
                contratos = await client.fetch_contratos(data_inicio, data_fim, page_size=100)
                sessoes = [c for c in contratos if c.get("cnpjOrgao") == orgao_cnpj]
                perfis = _agregar_por_pregoeiro(sessoes, [])
                for p in perfis:
                    import json
                    await conn.execute(
                        """INSERT INTO pregoeiro_profiles
                           (nome, nome_normalizado, orgao_cnpj, orgao_nome, total_sessoes,
                            taxa_aceitacao_impugnacao_pct, taxa_desclassificacao_pct,
                            tempo_medio_sessao_horas, previsibilidade,
                            empresas_frequentes_vencedoras, ultima_atualizacao)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
                           ON CONFLICT (nome_normalizado, orgao_cnpj) DO UPDATE SET
                               total_sessoes = EXCLUDED.total_sessoes,
                               taxa_aceitacao_impugnacao_pct = EXCLUDED.taxa_aceitacao_impugnacao_pct,
                               taxa_desclassificacao_pct = EXCLUDED.taxa_desclassificacao_pct,
                               tempo_medio_sessao_horas = EXCLUDED.tempo_medio_sessao_horas,
                               previsibilidade = EXCLUDED.previsibilidade,
                               empresas_frequentes_vencedoras = EXCLUDED.empresas_frequentes_vencedoras,
                               ultima_atualizacao = NOW()""",
                        p["nome"], p["nome_normalizado"], p["orgao_cnpj"], p["orgao_nome"],
                        p["total_sessoes"], p["taxa_aceitacao_impugnacao_pct"],
                        p["taxa_desclassificacao_pct"], p["tempo_medio_sessao_horas"],
                        p["previsibilidade"],
                        json.dumps(p["empresas_frequentes_vencedoras"]),
                    )
            except Exception as exc:
                logger.warning("pregoeiro_worker: orgao %s error: %s", orgao_cnpj, exc)

    await conn.close()
    logger.info("pregoeiro_worker: done — processed %d orgaos", len(orgao_cnpjs[:20]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_pregoeiro_update())
