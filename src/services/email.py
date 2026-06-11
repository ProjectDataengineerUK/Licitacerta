"""EmailService — e-mails transacionais via Resend HTTP API.

Sem RESEND_API_KEY configurado: loga warning e retorna sem crash (dev/CI).
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"
_FROM = os.getenv("RESEND_FROM_EMAIL", "LicitaCerta <noreply@licitacerta.com.br>")


async def send_digest_email(to: str, html: str, subject: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY ausente — digest não enviado para %s", to)
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": _FROM, "to": [to], "subject": subject, "html": html},
            )
        if r.status_code >= 400:
            logger.error("Resend error %s: %s", r.status_code, r.text)
            return False
        return True
    except Exception as exc:
        logger.error("Falha ao enviar digest para %s: %s", to, exc)
        return False


async def send_invite_email(to: str, invite_url: str, tenant_name: str) -> bool:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY ausente — convite não enviado para %s (url: %s)", to, invite_url)
        return False

    html = f"""
    <h2>Você foi convidado para {tenant_name} no LicitaCerta</h2>
    <p>Clique no botão abaixo para aceitar o convite e acessar a plataforma:</p>
    <p><a href="{invite_url}"
       style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;"
       >Aceitar convite</a></p>
    <p style="color:#6b7280;font-size:12px;">Este link expira em 7 dias.
    Se você não esperava este convite, ignore este e-mail.</p>
    """

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": _FROM, "to": [to], "subject": f"Convite — {tenant_name} no LicitaCerta", "html": html},
            )
        if r.status_code >= 400:
            logger.error("Resend error %s: %s", r.status_code, r.text)
            return False
        return True
    except Exception as exc:
        logger.error("Falha ao enviar e-mail de convite para %s: %s", to, exc)
        return False
