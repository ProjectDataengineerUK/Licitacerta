"""NOTIFICACOES_MULTICANAL — dispatcher multicanal.

Canais implementam `Channel`; o dispatcher aplica preferências do tenant (canal/
tipo/horário), deduplica (janela 4h) e marca os flags de envio. Integrações reais
(Resend/Z-API/FCM) ficam atrás das interfaces — v1 usa senders injetáveis/mock.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime, time, timedelta

import httpx

from src.api.alert_store import Alert, NotificationPreferences

logger = logging.getLogger(__name__)

_DEDUP_WINDOW = timedelta(hours=4)
Sender = Callable[[Alert, NotificationPreferences], Awaitable[bool]]


def _parse_time(value: str) -> time:
    h, m = value.split(":")
    return time(int(h), int(m))


class Channel(ABC):
    name: str = "channel"

    @abstractmethod
    def enabled_for(self, prefs: NotificationPreferences) -> bool:
        ...

    @abstractmethod
    async def send(self, alert: Alert, prefs: NotificationPreferences) -> bool:
        ...


class EmailChannel(Channel):
    name = "email"

    def __init__(self, sender: Sender | None = None) -> None:
        self._sender = sender

    def enabled_for(self, prefs: NotificationPreferences) -> bool:
        return prefs.email_enabled

    async def send(self, alert: Alert, prefs: NotificationPreferences) -> bool:
        if self._sender is None:
            logger.info("EmailChannel (no-op): %s → tenant %s", alert.tipo, alert.tenant_id)
            return True
        return await self._sender(alert, prefs)


class WhatsAppChannel(Channel):
    name = "whatsapp"

    def __init__(self, sender: Sender | None = None) -> None:
        self._sender = sender

    def enabled_for(self, prefs: NotificationPreferences) -> bool:
        return prefs.whatsapp_enabled and bool(prefs.whatsapp_number)

    async def send(self, alert: Alert, prefs: NotificationPreferences) -> bool:
        if self._sender is None:
            logger.info("WhatsAppChannel (no-op/feature-flag off): %s", alert.tipo)
            return True
        return await self._sender(alert, prefs)


class WebhookChannel(Channel):
    name = "webhook"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def enabled_for(self, prefs: NotificationPreferences) -> bool:
        return bool(prefs.webhook_url)

    @staticmethod
    def signature(payload: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    async def send(self, alert: Alert, prefs: NotificationPreferences) -> bool:
        assert prefs.webhook_url
        payload = json.dumps(alert.model_dump(mode="json"), sort_keys=True).encode()
        headers = {"Content-Type": "application/json"}
        if prefs.webhook_secret:
            headers["X-Signature"] = self.signature(payload, prefs.webhook_secret)
        try:
            resp = await self._client.post(prefs.webhook_url, content=payload, headers=headers)
            return resp.status_code < 300
        except Exception as exc:  # noqa: BLE001 — falha de webhook não derruba envio
            logger.warning("webhook falhou: %s", exc)
            return False


class NotificationDispatcher:
    def __init__(
        self,
        channels: list[Channel],
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._channels = channels
        self._now = now_provider or datetime.now
        self._last_sent: dict[tuple[str, str | None, str], datetime] = {}

    def _tipo_enabled(self, prefs: NotificationPreferences, tipo: str) -> bool:
        habilitados = prefs.tipos_habilitados or ["all"]
        return "all" in habilitados or tipo in habilitados

    def _within_hours(self, prefs: NotificationPreferences, now: datetime) -> bool:
        inicio = _parse_time(prefs.horario_inicio)
        fim = _parse_time(prefs.horario_fim)
        return inicio <= now.time() <= fim

    def _is_dup(self, alert: Alert, now: datetime) -> bool:
        key = (alert.tenant_id, alert.entidade_id, alert.tipo)
        last = self._last_sent.get(key)
        return last is not None and (now - last) < _DEDUP_WINDOW

    async def dispatch(self, alert: Alert, prefs: NotificationPreferences) -> dict[str, bool]:
        """Envia o alerta pelos canais aplicáveis. Retorna {canal: enviado}."""
        now = self._now()

        if not self._tipo_enabled(prefs, alert.tipo):
            return {}
        # críticos furam a janela de silêncio (prazo de disputa, certidão vencida, HITL)
        if alert.severidade != "critical" and not self._within_hours(prefs, now):
            return {}
        if self._is_dup(alert, now):
            return {}

        self._last_sent[(alert.tenant_id, alert.entidade_id, alert.tipo)] = now

        results: dict[str, bool] = {}
        for ch in self._channels:
            if not ch.enabled_for(prefs):
                continue
            ok = await ch.send(alert, prefs)
            results[ch.name] = ok
            if ok:
                setattr(alert, f"enviado_{ch.name}", True)
        return results
