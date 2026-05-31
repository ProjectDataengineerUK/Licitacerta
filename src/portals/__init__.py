"""MULTI_PORTAL — monitoramento de editais em múltiplos portais de compras.

Núcleo extensível: cada portal implementa ``PortalAdapter``; o ``PortalOrchestrator``
coordena todos em paralelo, isola falhas e deduplica por ``dedup_hash``.
"""
from src.portals.base import (
    PortalAdapter,
    PortalFilter,
    PortalHealthStatus,
    RawEdital,
    dedup_hash,
)
from src.portals.orchestrator import PortalOrchestrator, PortalRunResult

__all__ = [
    "PortalAdapter",
    "PortalFilter",
    "PortalHealthStatus",
    "RawEdital",
    "dedup_hash",
    "PortalOrchestrator",
    "PortalRunResult",
]
