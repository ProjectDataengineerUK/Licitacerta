"""Cloud Scheduler daily job: detect drift across all agents + alert on issues."""
from __future__ import annotations

import asyncio
import logging

from src.sentinela.drift_detector import DriftDetector
from src.sentinela.data_quality_checker import check_all_sources

logger = logging.getLogger(__name__)

AGENTS = ["compliance", "bid_no_bid", "impugnacao"]


async def run_drift_check() -> None:
    detector = DriftDetector()
    for agent in AGENTS:
        report = detector.detect_output_drift(agent)
        if report.drift_detected:
            logger.warning(
                "DRIFT_DETECTED agent=%s kl=%.4f current_n=%d",
                agent,
                report.kl_divergence,
                report.current_sample_n,
            )
            try:
                from src.api.notification_dispatcher import NotificationDispatcher
                await NotificationDispatcher.send_alert(
                    level="warning",
                    message=(
                        f"Drift detectado em {agent}: KL={report.kl_divergence:.4f} "
                        f"(threshold={0.1}). Verifique o prompt ativo."
                    ),
                )
            except Exception as exc:
                logger.warning("drift alert send failed: %s", exc)


async def run_data_quality_check() -> None:
    results = await check_all_sources()
    for health in results:
        if not health.is_fresh:
            logger.warning(
                "DATA_SOURCE_STALE source=%s error=%s latency_ms=%s",
                health.source_name,
                health.error,
                health.latency_ms,
            )
            try:
                from src.api.notification_dispatcher import NotificationDispatcher
                await NotificationDispatcher.send_alert(
                    level="critical",
                    message=f"Fonte {health.source_name} indisponível: {health.error}",
                )
            except Exception as exc:
                logger.warning("source alert send failed: %s", exc)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("sentinela_drift_job: starting")
    await asyncio.gather(
        run_drift_check(),
        run_data_quality_check(),
        return_exceptions=True,
    )
    logger.info("sentinela_drift_job: done")


if __name__ == "__main__":
    asyncio.run(main())
