from __future__ import annotations

import asyncio
import logging
import os
from datetime import date

from src.services import certidao_service as svc

logger = logging.getLogger(__name__)

_PROFISSIONAL_PLANS = {"profissional", "business", "enterprise"}

_TIPO_LABEL = {
    "CND_FEDERAL": "CND Federal",
    "FGTS": "Certidão de FGTS",
    "TRABALHISTA": "Certidão Trabalhista (CNDT)",
    "ESTADUAL_SEFAZ": "Certidão Estadual (SEFAZ)",
    "MUNICIPAL_ISSQN": "Certidão Municipal (ISSQN)",
}


class CertidaoMonitorWorker:
    def __init__(self, pool, dispatcher, prefs_provider, *, hoje: date | None = None) -> None:
        self._pool = pool
        self._dispatcher = dispatcher
        self._prefs_provider = prefs_provider
        self._hoje = hoje or date.today()

    async def run(self) -> dict:
        enviados, pulados, recalculados = 0, 0, 0

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, tenant_id, cnpj, tipo, validade, status, ultimo_alerta
                     FROM certidoes
                    WHERE validade IS NOT NULL AND status <> 'nao_verificada'
                    ORDER BY validade ASC"""
            )

        for r in rows:
            novo_status = svc.calculate_status(r["validade"], hoje=self._hoje)
            if novo_status != r["status"]:
                try:
                    async with self._pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE certidoes SET status=$2 WHERE id=$1", r["id"], novo_status
                        )
                    recalculados += 1
                except Exception as exc:
                    logger.warning(
                        "certidao_monitor: update status falhou id=%s: %s", r["id"], exc
                    )

            decisao = svc.check_alertas(r["validade"], r["ultimo_alerta"], hoje=self._hoje)
            if not decisao.deve_alertar:
                pulados += 1
                continue

            try:
                plan, prefs = await self._prefs_provider(r["tenant_id"])
            except Exception as exc:
                logger.warning(
                    "certidao_monitor: prefs falhou tenant=%s: %s", r["tenant_id"], exc
                )
                pulados += 1
                continue
            if plan not in _PROFISSIONAL_PLANS:
                pulados += 1
                continue

            ok = await self._dispatch(r, decisao, prefs)
            if ok:
                try:
                    async with self._pool.acquire() as conn:
                        await svc.marcar_alertado(conn, r["id"], self._hoje)
                    enviados += 1
                except Exception as exc:
                    logger.warning(
                        "certidao_monitor: marcar_alertado falhou id=%s: %s", r["id"], exc
                    )

        logger.info(
            "certidao_monitor: enviados=%d pulados=%d recalculados=%d total=%d",
            enviados,
            pulados,
            recalculados,
            len(rows),
        )
        return {"enviados": enviados, "pulados": pulados, "recalculados": recalculados}

    async def _dispatch(self, row, decisao, prefs) -> bool:
        from src.api.alert_store import Alert

        label = _TIPO_LABEL.get(row["tipo"], row["tipo"])
        if decisao.dias_restantes is not None and decisao.dias_restantes < 0:
            titulo = f"{label} VENCIDA"
            msg = f"A {label} (CNPJ {row['cnpj']}) venceu em {row['validade'].isoformat()}."
        else:
            titulo = f"{label} vence em {decisao.dias_restantes} dia(s)"
            msg = (
                f"A {label} (CNPJ {row['cnpj']}) vence em {row['validade'].isoformat()}. "
                "Regularize para não perder prazos de habilitação."
            )

        alert = Alert(
            id=str(row["id"]),
            tenant_id=row["tenant_id"],
            tipo="certidao_vencendo",
            titulo=titulo,
            severidade=decisao.severidade,
            mensagem=msg,
            link_relativo="/certidoes",
        )
        try:
            results = await self._dispatcher.dispatch(alert, prefs)
            return any(results.values()) if results else False
        except Exception as exc:
            logger.warning("certidao_monitor: dispatch falhou id=%s: %s", row["id"], exc)
            return False


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from src.services.notifications import EmailChannel, NotificationDispatcher
    from src.api.alert_store import NotificationPreferences

    pool = await _build_pool()
    dispatcher = NotificationDispatcher(channels=[EmailChannel()])

    async def prefs_provider(tenant_id: str):
        plan = os.environ.get("CERTIDAO_FORCE_PLAN", "profissional")
        return plan, NotificationPreferences(tenant_id=tenant_id)

    if pool is None:
        logger.warning("certidao_monitor_job: pool indisponível — abortando sem erro")
        return

    worker = CertidaoMonitorWorker(pool, dispatcher, prefs_provider)
    try:
        await worker.run()
    finally:
        await pool.close()


async def _build_pool():
    try:
        import asyncpg

        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            return None
        return await asyncpg.create_pool(dsn, min_size=1, max_size=4)
    except Exception as exc:
        logger.warning("certidao_monitor_job: build pool falhou: %s", exc)
        return None


if __name__ == "__main__":
    asyncio.run(main())
