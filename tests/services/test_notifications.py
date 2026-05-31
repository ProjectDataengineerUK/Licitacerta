"""NOTIFICACOES_MULTICANAL — dispatcher multicanal."""
from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient, MockTransport, Response

from src.api.alert_store import Alert, NotificationPreferences
from src.services.notifications import (
    EmailChannel,
    NotificationDispatcher,
    WebhookChannel,
    WhatsAppChannel,
)

_DAY = datetime(2026, 6, 1, 10, 0)
_NIGHT = datetime(2026, 6, 1, 23, 30)


def _alert(**over) -> Alert:
    base = dict(
        id="a1", tenant_id="t1", tipo="novo_edital_compativel", severidade="info",
        titulo="Novo edital", entidade_id="ed1",
    )
    base.update(over)
    return Alert(**base)


def _recording():
    sent = []

    async def sender(alert, prefs):
        sent.append(alert.tipo)
        return True

    return sent, sender


async def test_at001_email_enviado_no_horario():
    sent, sender = _recording()
    disp = NotificationDispatcher([EmailChannel(sender=sender)], now_provider=lambda: _DAY)
    alert = _alert()
    res = await disp.dispatch(alert, NotificationPreferences(tenant_id="t1"))
    assert res == {"email": True}
    assert sent == ["novo_edital_compativel"]
    assert alert.enviado_email is True


async def test_at002_horario_bloqueado_suprime():
    sent, sender = _recording()
    disp = NotificationDispatcher([EmailChannel(sender=sender)], now_provider=lambda: _NIGHT)
    res = await disp.dispatch(_alert(severidade="info"), NotificationPreferences(tenant_id="t1"))
    assert res == {}  # fora de 07-22
    assert sent == []


async def test_at008_critico_fura_horario():
    sent, sender = _recording()
    wpp_sent, wpp_sender = _recording()
    disp = NotificationDispatcher(
        [EmailChannel(sender=sender), WhatsAppChannel(sender=wpp_sender)],
        now_provider=lambda: _NIGHT,
    )
    prefs = NotificationPreferences(tenant_id="t1", whatsapp_enabled=True, whatsapp_number="+5511999999999")
    res = await disp.dispatch(_alert(tipo="hitl_pendente", severidade="critical"), prefs)
    assert res == {"email": True, "whatsapp": True}


async def test_at003_dedup_em_4h():
    sent, sender = _recording()
    disp = NotificationDispatcher([EmailChannel(sender=sender)], now_provider=lambda: _DAY)
    prefs = NotificationPreferences(tenant_id="t1")
    assert await disp.dispatch(_alert(), prefs) == {"email": True}
    assert await disp.dispatch(_alert(), prefs) == {}  # duplicata na janela
    assert sent == ["novo_edital_compativel"]


async def test_at004_whatsapp_desabilitado():
    e_sent, e_sender = _recording()
    w_sent, w_sender = _recording()
    disp = NotificationDispatcher(
        [EmailChannel(sender=e_sender), WhatsAppChannel(sender=w_sender)],
        now_provider=lambda: _DAY,
    )
    res = await disp.dispatch(_alert(), NotificationPreferences(tenant_id="t1"))  # whatsapp off por padrão
    assert "whatsapp" not in res
    assert res == {"email": True}
    assert w_sent == []


async def test_at005_webhook_hmac():
    captured: dict = {}

    def handler(req):
        captured["sig"] = req.headers.get("X-Signature")
        captured["body"] = req.content
        return Response(200)

    client = AsyncClient(transport=MockTransport(handler))
    disp = NotificationDispatcher([WebhookChannel(client=client)], now_provider=lambda: _DAY)
    prefs = NotificationPreferences(
        tenant_id="t1", webhook_url="https://hook.test/x", webhook_secret="s3cr3t"
    )
    res = await disp.dispatch(_alert(), prefs)
    await client.aclose()

    assert res == {"webhook": True}
    assert captured["sig"] == WebhookChannel.signature(captured["body"], "s3cr3t")


async def test_tipo_desabilitado_suprime():
    sent, sender = _recording()
    disp = NotificationDispatcher([EmailChannel(sender=sender)], now_provider=lambda: _DAY)
    prefs = NotificationPreferences(tenant_id="t1", tipos_habilitados=["prazo_disputa"])
    res = await disp.dispatch(_alert(tipo="novo_edital_compativel"), prefs)
    assert res == {}


@pytest.mark.parametrize("enabled,number,expected", [
    (True, "+5511999999999", True),
    (True, None, False),
    (False, "+5511999999999", False),
])
def test_whatsapp_enabled_for(enabled, number, expected):
    ch = WhatsAppChannel()
    prefs = NotificationPreferences(tenant_id="t1", whatsapp_enabled=enabled, whatsapp_number=number)
    assert ch.enabled_for(prefs) is expected
