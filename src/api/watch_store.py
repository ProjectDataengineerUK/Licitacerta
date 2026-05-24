from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class WatchConfig:
    id: UUID
    keywords: list[str]
    cnpj: str
    active: bool = True
    last_polled_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WatchedEdital:
    id: UUID
    pncp_id: str
    watch_config_id: UUID
    run_id: str
    triggered_at: datetime = field(default_factory=datetime.utcnow)


class WatchStore:
    def __init__(self) -> None:
        self._configs: dict[UUID, WatchConfig] = {}
        self._watched: dict[str, WatchedEdital] = {}
        self._lock = asyncio.Lock()

    async def create_config(self, keywords: list[str], cnpj: str) -> WatchConfig:
        cfg = WatchConfig(id=uuid4(), keywords=keywords, cnpj=cnpj)
        async with self._lock:
            self._configs[cfg.id] = cfg
        return cfg

    async def list_configs(self) -> list[WatchConfig]:
        async with self._lock:
            return list(self._configs.values())

    async def delete_config(self, config_id: UUID) -> bool:
        async with self._lock:
            return self._configs.pop(config_id, None) is not None

    async def is_seen(self, pncp_id: str) -> bool:
        async with self._lock:
            return pncp_id in self._watched

    async def record(
        self, pncp_id: str, watch_config_id: UUID, run_id: str
    ) -> WatchedEdital:
        entry = WatchedEdital(
            id=uuid4(),
            pncp_id=pncp_id,
            watch_config_id=watch_config_id,
            run_id=run_id,
        )
        async with self._lock:
            self._watched[pncp_id] = entry
        return entry

    async def update_polled_at(self, config_id: UUID) -> None:
        async with self._lock:
            if config_id in self._configs:
                self._configs[config_id].last_polled_at = datetime.utcnow()
