from __future__ import annotations

import logging
from decimal import Decimal

from src.schemas.market import (
    CompetitorProfile,
    OrganScore,
    PriceBenchmark,
)

logger = logging.getLogger(__name__)

_MIN_SAMPLE = 3  # retorna data_insuficiente abaixo deste mínimo


class MarketIntelService:
    def __init__(self, db) -> None:
        self._db = db  # asyncpg Connection / Pool

    async def competitor_xray(self, cnpj: str) -> CompetitorProfile:
        row = await self._db.fetchrow(
            """
            SELECT
                COUNT(*)::int                                   AS total_vitorias,
                AVG(valor_global)::numeric                      AS preco_medio,
                MAX(data_contrato)                              AS ultima_participacao,
                ARRAY(
                    SELECT DISTINCT orgao_nome
                    FROM market_contracts
                    WHERE fornecedor_cnpj = $1
                    ORDER BY orgao_nome
                    LIMIT 5
                )                                               AS top_orgaos
            FROM market_contracts
            WHERE fornecedor_cnpj = $1
            """,
            cnpj,
        )
        total = row["total_vitorias"] or 0
        taxa = 0.0
        if total > 0:
            total_orgaos = await self._db.fetchval(
                "SELECT COUNT(DISTINCT orgao_cnpj) FROM market_contracts"
            ) or 1
            taxa = round(min(1.0, total / total_orgaos) * 100, 2)

        nome_row = await self._db.fetchval(
            "SELECT fornecedor_nome FROM market_contracts WHERE fornecedor_cnpj = $1 LIMIT 1",
            cnpj,
        )

        # Verifica dominância: >40% dos contratos do segmento mais frequente
        dominante = False
        if total >= 10:
            share = await self._db.fetchval(
                """
                SELECT COUNT(*) * 1.0 / NULLIF(
                    (SELECT COUNT(*) FROM market_contracts
                     WHERE segmento_cnae = (
                         SELECT segmento_cnae FROM market_contracts
                         WHERE fornecedor_cnpj = $1
                         GROUP BY segmento_cnae ORDER BY COUNT(*) DESC LIMIT 1
                     )), 0)
                FROM market_contracts
                WHERE fornecedor_cnpj = $1
                """,
                cnpj,
            )
            dominante = bool(share and share > 0.40)

        return CompetitorProfile(
            cnpj=cnpj,
            nome=nome_row,
            taxa_vitoria_pct=taxa,
            total_vitorias=total,
            top_orgaos=list(row["top_orgaos"] or []),
            preco_medio_brl=Decimal(str(row["preco_medio"])) if row["preco_medio"] else None,
            ultima_participacao=row["ultima_participacao"],
            dominante=dominante,
        )

    async def price_benchmark(
        self,
        item: str,
        catmat_code: str | None = None,
        orgao_cnpj: str | None = None,
    ) -> PriceBenchmark:
        orgao_filter = "AND orgao_cnpj = $3" if orgao_cnpj else ""


        if catmat_code:
            sql = f"""
            SELECT
                COUNT(*)::int                              AS amostra,
                AVG(valor_unitario)::numeric               AS media,
                MIN(valor_unitario)::numeric               AS minimo,
                MAX(valor_unitario)::numeric               AS maximo,
                percentile_cont(0.25) WITHIN GROUP
                    (ORDER BY valor_unitario)::numeric     AS p25,
                percentile_cont(0.75) WITHIN GROUP
                    (ORDER BY valor_unitario)::numeric     AS p75
            FROM market_items
            WHERE catmat_code = $1 {orgao_filter}
            """
            params = [catmat_code, *(([orgao_cnpj]) if orgao_cnpj else [])]
            method = "catmat"
            confidence = 1.0
        else:
            normalizado = " ".join(item.lower().split())
            sql = f"""
            SELECT
                COUNT(*)::int                              AS amostra,
                AVG(valor_unitario)::numeric               AS media,
                MIN(valor_unitario)::numeric               AS minimo,
                MAX(valor_unitario)::numeric               AS maximo,
                percentile_cont(0.25) WITHIN GROUP
                    (ORDER BY valor_unitario)::numeric     AS p25,
                percentile_cont(0.75) WITHIN GROUP
                    (ORDER BY valor_unitario)::numeric     AS p75
            FROM market_items
            WHERE similarity(descricao_normalizada, $1) > 0.3 {orgao_filter}
            """
            params = [normalizado, *(([orgao_cnpj]) if orgao_cnpj else [])]
            method = "trigram"
            confidence = 0.7

        row = await self._db.fetchrow(sql, *params)
        amostra = row["amostra"] or 0

        if amostra < _MIN_SAMPLE:
            return PriceBenchmark(
                item_descricao=item,
                match_method=method,
                match_confidence=confidence,
                amostra=amostra,
                data_insuficiente=True,
            )

        tendencia = await self._calc_tendencia(catmat_code, item)

        return PriceBenchmark(
            item_descricao=item,
            match_method=method,
            match_confidence=confidence,
            amostra=amostra,
            media_brl=Decimal(str(row["media"])) if row["media"] else None,
            min_brl=Decimal(str(row["minimo"])) if row["minimo"] else None,
            max_brl=Decimal(str(row["maximo"])) if row["maximo"] else None,
            percentil_25=Decimal(str(row["p25"])) if row["p25"] else None,
            percentil_75=Decimal(str(row["p75"])) if row["p75"] else None,
            tendencia_12m_pct=tendencia,
            data_insuficiente=False,
        )

    async def _calc_tendencia(self, catmat_code: str | None, item: str) -> float | None:
        try:
            if catmat_code:
                rows = await self._db.fetch(
                    """
                    SELECT date_trunc('month', data_contrato) AS mes,
                           AVG(valor_unitario) AS media
                    FROM market_items
                    WHERE catmat_code = $1
                      AND data_contrato >= NOW() - INTERVAL '12 months'
                    GROUP BY mes ORDER BY mes
                    """,
                    catmat_code,
                )
            else:
                normalizado = " ".join(item.lower().split())
                rows = await self._db.fetch(
                    """
                    SELECT date_trunc('month', data_contrato) AS mes,
                           AVG(valor_unitario) AS media
                    FROM market_items
                    WHERE similarity(descricao_normalizada, $1) > 0.3
                      AND data_contrato >= NOW() - INTERVAL '12 months'
                    GROUP BY mes ORDER BY mes
                    """,
                    normalizado,
                )
            if len(rows) < 2:
                return None
            primeiro = float(rows[0]["media"])
            ultimo = float(rows[-1]["media"])
            if primeiro == 0:
                return None
            return round((ultimo - primeiro) / primeiro * 100, 2)
        except Exception:
            return None

    async def organ_score(
        self, uasg: str | None = None, orgao_cnpj: str | None = None
    ) -> OrganScore:
        if not uasg and not orgao_cnpj:
            raise ValueError("uasg ou orgao_cnpj obrigatório")

        if uasg:
            filter_sql = "WHERE uasg = $1"
            param = uasg
        else:
            filter_sql = "WHERE orgao_cnpj = $1"
            param = orgao_cnpj

        row = await self._db.fetchrow(
            f"""
            SELECT
                COUNT(*)::int                                AS amostra,
                AVG(prazo_pagamento_dias)::numeric           AS prazo_medio,
                orgao_cnpj,
                MAX(orgao_nome)                             AS orgao_nome,
                MAX(uasg)                                   AS uasg,
                SUM(CASE WHEN prazo_pagamento_dias > 90 THEN 1 ELSE 0 END)
                    * 1.0 / NULLIF(COUNT(*), 0)             AS indice_inadimplencia
            FROM market_contracts
            {filter_sql}
            """,
            param,
        )

        amostra = row["amostra"] or 0
        if amostra < _MIN_SAMPLE:
            return OrganScore(
                uasg=uasg,
                orgao_cnpj=orgao_cnpj or "",
                score=50,
                label="Regular",
                amostra=amostra,
                data_insuficiente=True,
            )

        prazo = float(row["prazo_medio"] or 30)
        inadimplencia_pct = float(row["indice_inadimplencia"] or 0) * 100

        raw_score = 100 - max(0, prazo - 30) * 1.0 - inadimplencia_pct * 2.0
        score = int(max(0, min(100, raw_score)))

        if score >= 70:
            label = "Bom Pagador"
        elif score >= 40:
            label = "Regular"
        else:
            label = "Risco Alto"

        return OrganScore(
            uasg=row["uasg"] or uasg,
            orgao_cnpj=row["orgao_cnpj"] or orgao_cnpj or "",
            orgao_nome=row["orgao_nome"],
            score=score,
            label=label,
            prazo_medio_pagamento_dias=int(prazo),
            indice_inadimplencia_pct=round(inadimplencia_pct, 2),
            nivel_exigencia="baixo" if score >= 70 else ("medio" if score >= 40 else "alto"),
            amostra=amostra,
            alerta_inadimplencia=inadimplencia_pct > 0 and score < 50,
            data_insuficiente=False,
        )

    async def segment_summary(
        self, cnae: str
    ) -> dict:
        rows = await self._db.fetch(
            """
            SELECT
                fornecedor_cnpj,
                MAX(fornecedor_nome)  AS nome,
                COUNT(*)::int         AS total,
                COUNT(*) * 1.0 / NULLIF(
                    (SELECT COUNT(*) FROM market_contracts WHERE segmento_cnae = $1), 0
                ) AS share
            FROM market_contracts
            WHERE segmento_cnae = $1
            GROUP BY fornecedor_cnpj
            ORDER BY total DESC
            LIMIT 10
            """,
            cnae,
        )

        top: list[dict] = [
            {
                "cnpj": r["fornecedor_cnpj"],
                "nome": r["nome"],
                "total_contratos": r["total"],
                "share_pct": round(float(r["share"] or 0) * 100, 2),
            }
            for r in rows
        ]

        concentracao_alta = bool(top and top[0]["share_pct"] > 40)
        cnpj_dominante = top[0]["cnpj"] if concentracao_alta else None

        return {
            "segmento_cnae": cnae,
            "top_fornecedores": top,
            "concentracao_alta": concentracao_alta,
            "cnpj_dominante": cnpj_dominante,
        }
