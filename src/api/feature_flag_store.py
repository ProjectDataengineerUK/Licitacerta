"""FeatureFlagStore — feature flags por tenant com expiração automática."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

KNOWN_FEATURES = [
    "robo_lances",
    "multi_portal",
    "contract_agent_full",
    "inteligencia_competitiva",
    "precificacao_avancada",
    "antecipacao_recebiveis",
    "verticalizacao",
    "api_access",
]


class FeatureFlag(BaseModel):
    tenant_id: str
    feature: str
    enabled: bool = False
    override: bool = False
    expires_at: str | None = None
    note: str | None = None
    created_by: str | None = None
    updated_at: str = ""

    def model_post_init(self, _: Any) -> None:
        if not self.updated_at:
            self.updated_at = datetime.now(UTC).isoformat()

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now(UTC)

    def is_active(self) -> bool:
        return self.enabled and not self.is_expired()


class FeatureFlagStore:
    def __init__(self) -> None:
        # (tenant_id, feature) → FeatureFlag
        self._flags: dict[tuple[str, str], FeatureFlag] = {}

    def get(self, tenant_id: str, feature: str) -> FeatureFlag | None:
        flag = self._flags.get((tenant_id, feature))
        if flag and flag.is_expired():
            self._flags[(tenant_id, feature)] = flag.model_copy(
                update={"enabled": False, "updated_at": datetime.now(UTC).isoformat()}
            )
            return self._flags[(tenant_id, feature)]
        return flag

    def is_active(self, tenant_id: str, feature: str) -> bool:
        flag = self.get(tenant_id, feature)
        return flag.is_active() if flag else False

    def list_for_tenant(self, tenant_id: str) -> list[FeatureFlag]:
        return [
            self.get(tenant_id, feat) or FeatureFlag(tenant_id=tenant_id, feature=feat)
            for feat in KNOWN_FEATURES
        ]

    def set(
        self,
        tenant_id: str,
        feature: str,
        enabled: bool,
        override: bool = False,
        expires_at: str | None = None,
        note: str | None = None,
        created_by: str | None = None,
    ) -> FeatureFlag:
        flag = FeatureFlag(
            tenant_id=tenant_id,
            feature=feature,
            enabled=enabled,
            override=override,
            expires_at=expires_at,
            note=note,
            created_by=created_by,
        )
        self._flags[(tenant_id, feature)] = flag
        return flag
