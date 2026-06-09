"""Output drift detection using KL divergence on agent output distributions.

Compares distribution of categorical outputs (risk_level, recommendation)
over last 7 days vs. 30-day baseline. KL divergence > 0.1 = DRIFT_DETECTED.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

THRESHOLD_KL = 0.1
MIN_SAMPLES = 20

_OUTPUT_FIELDS: dict[str, str] = {
    "compliance":  "risk_level",
    "bid_no_bid":  "recommendation",
    "impugnacao":  "recommendation",
    "pricing":     "min_margin_pct",  # numeric → histogram
}


@dataclass
class DriftReport:
    agent_name: str
    drift_detected: bool
    kl_divergence: float = 0.0
    current_distribution: list[float] = field(default_factory=list)
    baseline_distribution: list[float] = field(default_factory=list)
    current_sample_n: int = 0
    baseline_sample_n: int = 0
    data_insuficiente: bool = False
    message: str = ""


class DriftDetector:
    def __init__(self, bq_client: Any = None) -> None:
        self._bq = bq_client

    def detect_output_drift(
        self,
        agent_name: str,
        window_days: int = 7,
        baseline_days: int = 30,
    ) -> DriftReport:
        try:
            current_dist, n_current = self._get_distribution(agent_name, window_days)
            baseline_dist, n_baseline = self._get_distribution(agent_name, baseline_days)

            if n_current < MIN_SAMPLES:
                return DriftReport(
                    agent_name=agent_name,
                    drift_detected=False,
                    data_insuficiente=True,
                    current_sample_n=n_current,
                    message=f"Dados insuficientes: {n_current} samples (mínimo {MIN_SAMPLES})",
                )

            eps = 1e-10
            kl = float(np.sum(np.where(
                current_dist > 0,
                current_dist * np.log((current_dist + eps) / (baseline_dist + eps)),
                0,
            )))

            return DriftReport(
                agent_name=agent_name,
                drift_detected=kl > THRESHOLD_KL,
                kl_divergence=kl,
                current_distribution=current_dist.tolist(),
                baseline_distribution=baseline_dist.tolist(),
                current_sample_n=n_current,
                baseline_sample_n=n_baseline,
                message="DRIFT_DETECTED" if kl > THRESHOLD_KL else "OK",
            )
        except Exception as exc:
            logger.warning("drift_detector: %s failed: %s", agent_name, exc)
            return DriftReport(
                agent_name=agent_name,
                drift_detected=False,
                data_insuficiente=True,
                message=f"Erro ao calcular drift: {exc}",
            )

    def _get_distribution(self, agent_name: str, days: int) -> tuple[np.ndarray, int]:
        """Query BigQuery for output distribution; return normalized vector + sample count."""
        if self._bq is None:
            return np.array([0.25, 0.25, 0.25, 0.25]), 0

        output_field = _OUTPUT_FIELDS.get(agent_name, "risk_level")
        try:
            query = f"""
                SELECT {output_field} AS bucket, COUNT(*) AS n
                FROM `licitacerta.agent_runs`
                WHERE agent_name = @agent_name
                  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
                GROUP BY bucket
                ORDER BY bucket
            """
            rows = self._bq.query(query, parameters={"agent_name": agent_name}).result()
            counts: dict[str, int] = {row.bucket: row.n for row in rows}
            total = sum(counts.values())
            if total == 0:
                return np.array([0.25, 0.25, 0.25, 0.25]), 0
            all_buckets = sorted(counts)
            vec = np.array([counts[b] / total for b in all_buckets])
            return vec, total
        except Exception as exc:
            logger.warning("drift_detector._get_distribution: %s", exc)
            return np.array([0.25, 0.25, 0.25, 0.25]), 0
