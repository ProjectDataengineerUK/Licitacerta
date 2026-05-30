from __future__ import annotations

import hashlib
from datetime import date, timedelta
from math import ceil
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_QUARTER_TO_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}


class ProcurementPrediction(BaseModel):
    id: str
    orgao_cnpj: str | None
    orgao_nome: str | None
    objeto_previsto: str | None
    valor_estimado_brl: float | None
    data_prevista_publicacao: str
    data_prevista_sessao: str | None
    confianca_pct: float
    fonte: str
    dias_antecedencia: int
    status: str


class RadarPredictor:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._emb_cache: dict[str, list[float]] = {}

    def calc_data_prevista(
        self,
        periodo_inicio: date | None,
        historico_mes: int | None,
    ) -> tuple[date, str]:
        today = date.today()
        ano = today.year

        if historico_mes and historico_mes > 0:
            d = date(ano, historico_mes, 1)
            if d < today:
                d = date(ano + 1, historico_mes, 1)
            return d, "sazonalidade"

        if periodo_inicio:
            q = ceil(periodo_inicio.month / 3)
            mes = _QUARTER_TO_MONTH.get(q, periodo_inicio.month)
            try:
                d = date(periodo_inicio.year, mes, 1)
            except ValueError:
                d = date(periodo_inicio.year, 1, 1)
            if d < today:
                d = date(ano + 1, mes, 1)
            return d, "pca"

        return today + timedelta(days=60), "pca"

    def calc_confianca(
        self,
        similarity_score: float,
        fonte: str,
        historico_count: int,
        periodo_inicio: date | None,
    ) -> float:
        base = similarity_score * 100

        if fonte == "combinado":
            base *= 1.20
        elif fonte == "sazonalidade" and historico_count >= 3:
            base *= 1.15
        elif fonte == "pca" and periodo_inicio:
            base *= 1.05

        if historico_count == 0 and fonte == "pca":
            base *= 0.80

        return min(round(base, 1), 100.0)

    async def generate_for_tenant(
        self,
        tenant_id: UUID,
        segmentos_interesse: list[str],
        threshold: float = 0.50,
    ) -> list[ProcurementPrediction]:
        if not segmentos_interesse:
            return []

        embedder = _get_embedder()
        if embedder is None:
            return []

        perfil_texto = " ".join(segmentos_interesse)
        perfil_emb = await _safe_embed_query(embedder, perfil_texto)
        if not perfil_emb:
            return []

        rows = await self._session.execute(
            text("""
                SELECT id, orgao_cnpj, orgao_nome, descricao, valor_estimado_brl,
                       periodo_inicio, periodo_fim, segmento_cnae
                FROM pca_items
                WHERE status = 'planejado'
                  AND (periodo_fim IS NULL OR periodo_fim >= :hoje)
                LIMIT 500
            """),
            {"hoje": date.today()},
        )
        items = rows.fetchall()
        if not items:
            return []

        descricoes = [r.descricao for r in items]
        embeddings = await self._embed_batch(embedder, descricoes)

        predictions: list[ProcurementPrediction] = []
        for row, emb in zip(items, embeddings):
            if not emb:
                continue
            score = _cosine(perfil_emb, emb)
            if score < threshold:
                continue

            hist_mes, hist_count = await self._get_seasonality(row.orgao_cnpj, row.segmento_cnae)
            data_prev, fonte = self.calc_data_prevista(row.periodo_inicio, hist_mes)
            if hist_mes:
                fonte = "combinado"

            confianca = self.calc_confianca(score, fonte, hist_count, row.periodo_inicio)
            if confianca < 20:
                continue

            data_sessao = data_prev + timedelta(days=25)
            await self._upsert_prediction(
                tenant_id=tenant_id,
                pca_id=row.id,
                orgao_cnpj=row.orgao_cnpj,
                orgao_nome=row.orgao_nome,
                objeto=row.descricao,
                valor=row.valor_estimado_brl,
                data_prev=data_prev,
                data_sessao=data_sessao,
                confianca=confianca,
                fonte=fonte,
            )
            predictions.append(ProcurementPrediction(
                id=str(row.id),
                orgao_cnpj=row.orgao_cnpj,
                orgao_nome=row.orgao_nome,
                objeto_previsto=row.descricao,
                valor_estimado_brl=float(row.valor_estimado_brl) if row.valor_estimado_brl else None,
                data_prevista_publicacao=data_prev.isoformat(),
                data_prevista_sessao=data_sessao.isoformat(),
                confianca_pct=confianca,
                fonte=fonte,
                dias_antecedencia=(data_prev - date.today()).days,
                status="pendente",
            ))

        return predictions

    async def cross_reference(self, edital_objeto: str, orgao_cnpj: str) -> None:
        embedder = _get_embedder()
        if embedder is None:
            return

        edital_emb = await _safe_embed_query(embedder, edital_objeto)
        if not edital_emb:
            return

        rows = await self._session.execute(
            text("""
                SELECT id, objeto_previsto FROM procurement_predictions
                WHERE orgao_cnpj = :cnpj
                  AND edital_publicado_id IS NULL
                  AND data_prevista_publicacao BETWEEN :d_min AND :d_max
            """),
            {
                "cnpj": orgao_cnpj,
                "d_min": date.today() - timedelta(days=90),
                "d_max": date.today() + timedelta(days=90),
            },
        )
        for row in rows.fetchall():
            if not row.objeto_previsto:
                continue
            pred_emb = await _safe_embed_query(embedder, row.objeto_previsto)
            if pred_emb and _cosine(edital_emb, pred_emb) >= 0.70:
                await self._session.execute(
                    text("""
                        UPDATE procurement_predictions
                        SET edital_publicado_id = :eid, status = 'confirmado'
                        WHERE id = :pid
                    """),
                    {"eid": orgao_cnpj, "pid": str(row.id)},
                )

    async def _get_seasonality(self, orgao_cnpj, segmento_cnae) -> tuple[int | None, int]:
        if not orgao_cnpj or not segmento_cnae:
            return None, 0
        try:
            row = await self._session.execute(
                text("""
                    SELECT EXTRACT(MONTH FROM data_contrato)::int AS mes,
                           COUNT(DISTINCT EXTRACT(YEAR FROM data_contrato)) AS anos
                    FROM market_contracts
                    WHERE orgao_cnpj = :cnpj AND segmento_cnae = :seg
                    GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1
                """),
                {"cnpj": orgao_cnpj, "seg": segmento_cnae},
            )
            r = row.fetchone()
            return (r.mes, int(r.anos)) if r else (None, 0)
        except Exception:
            return None, 0

    async def _embed_batch(self, embedder, texts: list[str]) -> list[list[float] | None]:
        result: list[list[float] | None] = []
        to_embed: list[tuple[int, str]] = []
        for i, t in enumerate(texts):
            h = hashlib.sha256(t.encode()).hexdigest()[:16]
            if h in self._emb_cache:
                result.append(self._emb_cache[h])
            else:
                to_embed.append((i, t))
                result.append(None)
        if to_embed:
            idxs, txts = zip(*to_embed)
            try:
                embs = await embedder.aembed_documents(list(txts))
                for idx, emb, txt in zip(idxs, embs, txts):
                    h = hashlib.sha256(txt.encode()).hexdigest()[:16]
                    self._emb_cache[h] = emb
                    result[idx] = emb
            except Exception:
                pass
        return result

    async def _upsert_prediction(self, **kw) -> None:
        await self._session.execute(
            text("""
                INSERT INTO procurement_predictions
                    (tenant_id, pca_item_id, orgao_cnpj, orgao_nome, objeto_previsto,
                     valor_estimado_brl, data_prevista_publicacao, data_prevista_sessao,
                     confianca_pct, fonte)
                VALUES
                    (:tenant_id, :pca_id, :orgao_cnpj, :orgao_nome, :objeto,
                     :valor, :data_prev, :data_sessao, :confianca, :fonte)
                ON CONFLICT (tenant_id, pca_item_id) DO UPDATE SET
                    confianca_pct = EXCLUDED.confianca_pct,
                    data_prevista_publicacao = EXCLUDED.data_prevista_publicacao,
                    fonte = EXCLUDED.fonte
            """),
            {
                "tenant_id": str(kw["tenant_id"]),
                "pca_id": str(kw["pca_id"]),
                "orgao_cnpj": kw["orgao_cnpj"],
                "orgao_nome": kw["orgao_nome"],
                "objeto": kw["objeto"],
                "valor": kw["valor"],
                "data_prev": kw["data_prev"],
                "data_sessao": kw["data_sessao"],
                "confianca": kw["confianca"],
                "fonte": kw["fonte"],
            },
        )


def _get_embedder():
    try:
        from src.gcp.vertex_ai import VertexAIEmbeddings
        return VertexAIEmbeddings.from_env()
    except Exception:
        return None


async def _safe_embed_query(embedder, text_input: str) -> list[float] | None:
    try:
        return await embedder.aembed_query(text_input)
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
