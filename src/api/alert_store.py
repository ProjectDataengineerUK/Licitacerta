"""NOTIFICACOES_MULTICANAL — modelos + store em memória de alertas e preferências.

Fonte unificada de alertas do sistema (watch, vencimentos, impugnação, certidões,
HITL). In-memory no padrão do RunStore; migration AlloyDB é follow-up.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severidade = Literal["info", "warning", "critical"]


class AlertCreate(BaseModel):
    tenant_id: str
    tipo: str
    titulo: str
    severidade: Severidade = "info"
    mensagem: str = ""
    link_relativo: str | None = None
    entidade_tipo: str | None = None
    entidade_id: str | None = None


class Alert(BaseModel):
    id: str
    tenant_id: str
    tipo: str
    severidade: Severidade
    titulo: str
    mensagem: str = ""
    link_relativo: str | None = None
    entidade_tipo: str | None = None
    entidade_id: str | None = None
    lido: bool = False
    enviado_email: bool = False
    enviado_whatsapp: bool = False
    enviado_push: bool = False
    enviado_webhook: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class NotificationPreferences(BaseModel):
    tenant_id: str
    email_enabled: bool = True
    whatsapp_enabled: bool = False
    whatsapp_number: str | None = None
    push_enabled: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None
    horario_inicio: str = "07:00"
    horario_fim: str = "22:00"
    tipos_habilitados: list[str] = Field(default_factory=lambda: ["all"])


class AlertStore:
    def __init__(self) -> None:
        self._alerts: dict[str, Alert] = {}
        self._prefs: dict[str, NotificationPreferences] = {}
        self._lock = asyncio.Lock()

    async def create(self, body: AlertCreate) -> Alert:
        async with self._lock:
            aid = str(uuid.uuid4())
            alert = Alert(id=aid, **body.model_dump())
            self._alerts[aid] = alert
            return alert

    async def get(self, alert_id: str) -> Alert | None:
        async with self._lock:
            return self._alerts.get(alert_id)

    async def query(
        self,
        tenant_id: str | None = None,
        lido: bool | None = None,
        severidade: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Alert]:
        async with self._lock:
            items = list(self._alerts.values())
        if tenant_id is not None:
            items = [a for a in items if a.tenant_id == tenant_id]
        if lido is not None:
            items = [a for a in items if a.lido == lido]
        if severidade is not None:
            items = [a for a in items if a.severidade == severidade]
        items.sort(key=lambda a: a.created_at, reverse=True)
        start = (page - 1) * page_size
        return items[start : start + page_size]

    async def mark_read(self, ids: list[str]) -> int:
        async with self._lock:
            n = 0
            for aid in ids:
                a = self._alerts.get(aid)
                if a is not None and not a.lido:
                    a.lido = True
                    n += 1
            return n

    async def get_prefs(self, tenant_id: str) -> NotificationPreferences:
        async with self._lock:
            return self._prefs.get(tenant_id) or NotificationPreferences(tenant_id=tenant_id)

    async def set_prefs(self, prefs: NotificationPreferences) -> NotificationPreferences:
        async with self._lock:
            self._prefs[prefs.tenant_id] = prefs
            return prefs
