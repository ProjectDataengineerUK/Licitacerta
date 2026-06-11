from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConsentBody(BaseModel):
    accepted_tou: bool = Field(..., description="Aceite dos Termos de Uso")
    accepted_privacy: bool = Field(..., description="Aceite da Política de Privacidade")


class ConsentStatus(BaseModel):
    version: str
    has_consent: bool
    needs_consent: bool


class DeletionRequestOut(BaseModel):
    id: str
    tenant_id: str
    status: str
    scheduled_delete_at: datetime | None = None
    mensagem: str
