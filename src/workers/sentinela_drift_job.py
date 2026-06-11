"""Cloud Scheduler daily job: detect drift across all agents + alert on issues."""
from __future__ import annotations

import asyncio
import logging

from src.sentinela.data_quality_checker import check_all_sources
from src.sentinela.drift_detector import DriftDetector

logger = logging.getLogger(__name__)

AGENTS = ["compliance", "bid_no_bid", "impugnacao"]

OPS_ALERTS_TOPIC = "sentinela-ops-alerts"


async def _send_ops_alert(level: str, message: str) -> None:
    """Publica alerta operacional no Pub/Sub; sem GCP, loga em ERROR."""
    import os

    if not os.environ.get("GCP_PROJECT_ID"):
        logger.error("OPS_ALERT level=%s message=%s", level, message)
        return
    try:
        from src.gcp.pubsub import PubSubPublisher

        PubSubPublisher.from_env().publish_event(
            OPS_ALERTS_TOPIC, {"level": level, "message": message, "source": "sentinela"}
        )
    except Exception as exc:
        logger.error("OPS_ALERT publish failed (%s) level=%s message=%s", exc, level, message)


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
            await _send_ops_alert(
                "warning",
                f"Drift detectado em {agent}: KL={report.kl_divergence:.4f} "
                f"(threshold=0.1). Verifique o prompt ativo.",
            )


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
            await _send_ops_alert(
                "critical",
                f"Fonte {health.source_name} indisponível: {health.error}",
            )


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
