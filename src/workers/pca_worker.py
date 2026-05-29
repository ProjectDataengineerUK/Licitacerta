from __future__ import annotations

import asyncio
import json
import os
from datetime import date


def run() -> None:
    asyncio.run(_async_run())


async def _async_run() -> None:
    from sqlalchemy import text

    from src.agents.pca_classifier import PCAClassifierAgent
    from src.api.pncp_client import PNCPClient
    from src.config import settings
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory
    from src.services.radar_predictor import RadarPredictor

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    classifier = PCAClassifierAgent()
    ano = date.today().year

    async with PNCPClient() as pncp:
        orgs = await pncp.fetch_orgs_with_pca(ano)
        cnpjs = [o["cnpjOrgao"] for o in orgs if o.get("cnpjOrgao")]

        async with session_factory() as session:
            for cnpj in cnpjs[:200]:
                items = await pncp.fetch_pca_items(cnpj, ano)
                if not items:
                    continue
                descricoes = [it.get("descricaoItem", "") for it in items]
                classifications = await classifier.classify_batch(descricoes)
                for item, cls in zip(items, classifications):
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO pca_items
                                    (orgao_cnpj, orgao_nome, ano, numero_item, descricao,
                                     valor_estimado_brl, periodo_inicio, periodo_fim,
                                     categoria, segmento_cnae, raw_data)
                                VALUES (:orgao_cnpj, :orgao_nome, :ano, :num, :desc,
                                        :valor, :p_ini, :p_fim, :cat, :cnae, :raw::jsonb)
                                ON CONFLICT (orgao_cnpj, ano, numero_item) DO UPDATE SET
                                    segmento_cnae = EXCLUDED.segmento_cnae,
                                    categoria = EXCLUDED.categoria
                            """),
                            {
                                "orgao_cnpj": cnpj,
                                "orgao_nome": item.get("nomeOrgao"),
                                "ano": ano,
                                "num": str(item.get("numeroItem") or item.get("sequencialItem") or ""),
                                "desc": item.get("descricaoItem", ""),
                                "valor": item.get("valorEstimado"),
                                "p_ini": _parse_date(item.get("dataInicioPeriodo")),
                                "p_fim": _parse_date(item.get("dataFimPeriodo")),
                                "cat": cls.categoria,
                                "cnae": cls.segmento_cnae,
                                "raw": json.dumps(item, ensure_ascii=False),
                            },
                        )
                    except Exception:
                        continue
            await session.commit()

    async with session_factory() as session:
        tenants_rows = await session.execute(
            text("""
                SELECT id, vertical, segmentos_interesse
                FROM tenants
                WHERE subscription_status IN ('active', 'trial')
                  AND vertical IS NOT NULL
            """)
        )
        predictor = RadarPredictor(session)
        for t in tenants_rows.fetchall():
            segmentos = list(t.segmentos_interesse or [t.vertical])
            await predictor.generate_for_tenant(
                tenant_id=t.id,
                segmentos_interesse=segmentos,
            )
        await session.commit()

    await _dispatch_alerts(session_factory)


async def _dispatch_alerts(session_factory) -> None:
    if not os.environ.get("GCP_PROJECT_ID"):
        return
    from sqlalchemy import text
    from src.gcp.pubsub import PubSubPublisher

    publisher = PubSubPublisher.from_env()
    async with session_factory() as session:
        rows = await session.execute(
            text("""
                SELECT id, tenant_id, objeto_previsto, orgao_nome,
                       valor_estimado_brl, data_prevista_publicacao, confianca_pct
                FROM procurement_predictions
                WHERE confianca_pct >= 70
                  AND alerta_enviado = false
                  AND data_prevista_publicacao <= CURRENT_DATE + INTERVAL '40 days'
                  AND edital_publicado_id IS NULL
            """)
        )
        for row in rows.fetchall():
            try:
                publisher.publish_event("radar-alert-requested", {
                    "prediction_id": str(row.id),
                    "tenant_id": str(row.tenant_id),
                    "objeto": row.objeto_previsto or "",
                    "orgao": row.orgao_nome or "",
                    "data_prevista": row.data_prevista_publicacao.isoformat(),
                    "confianca": row.confianca_pct,
                })
            except Exception:
                continue
            await session.execute(
                text("UPDATE procurement_predictions SET alerta_enviado=true WHERE id=:id"),
                {"id": str(row.id)},
            )
        await session.commit()


def _parse_date(s):
    if not s:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(s)[:10]).date()
    except Exception:
        return None


if __name__ == "__main__":
    run()
