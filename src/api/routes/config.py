"""PAINEL_USUARIO — configurações self-service do tenant.

Endpoints: /config/empresa, /config/usuarios, /config/notificacoes,
           /config/dados/export, /config/dados (DELETE).
"""
from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.auth import require_user_role
from src.api.deps import (
    get_alert_store,
    get_contract_store,
    get_store,
    get_tenant_user_store,
)
from src.api.tenant_user_store import TenantUserStore
from src.services.email import send_invite_email

router = APIRouter(prefix="/config", tags=["config"])

_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _tenant(request: Request) -> str:
    return getattr(request.state, "tenant_id", "") or "dev-tenant"


# ── empresa ──────────────────────────────────────────────────────────────────


class TenantProfileOut(BaseModel):
    id: str
    name: str
    cnpj: str
    vertical: str | None = None
    segmentos: list[str] = []
    ufs_interesse: list[str] = []
    regime_tributario: str = "simples"


class TenantProfilePatch(BaseModel):
    name: str | None = None
    cnpj: str | None = None
    vertical: str | None = None
    segmentos: list[str] | None = None
    ufs_interesse: list[str] | None = None
    regime_tributario: str | None = None


_tenant_profiles: dict[str, dict] = {}


@router.get("/empresa", response_model=TenantProfileOut)
async def get_empresa(request: Request, _auth=Depends(require_user_role())):
    tid = _tenant(request)
    profile = _tenant_profiles.get(tid, {"id": tid, "name": tid, "cnpj": ""})
    return TenantProfileOut(**profile)


@router.patch("/empresa", response_model=TenantProfileOut)
async def patch_empresa(
    body: TenantProfilePatch,
    request: Request,
    _auth=Depends(require_user_role("admin")),
):
    tid = _tenant(request)
    current = _tenant_profiles.get(tid, {"id": tid, "name": tid, "cnpj": ""})
    update = body.model_dump(exclude_none=True)
    _tenant_profiles[tid] = {**current, **update}
    return TenantProfileOut(**_tenant_profiles[tid])


# ── usuários ─────────────────────────────────────────────────────────────────


class MemberOut(BaseModel):
    id: str
    user_uid: str
    email: str
    nome: str | None = None
    papel: str
    ativo: bool
    created_at: str


class InviteOut(BaseModel):
    id: str
    email: str
    papel: str
    expires_at: str
    accepted_at: str | None = None


class UsersListOut(BaseModel):
    members: list[MemberOut]
    invites: list[InviteOut]


class InviteBody(BaseModel):
    email: str
    papel: str = "analista"


class PapelBody(BaseModel):
    papel: str


VALID_ROLES = {"admin", "analista", "visualizador"}


@router.get("/usuarios", response_model=UsersListOut)
async def list_usuarios(
    request: Request,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role()),
):
    tid = _tenant(request)
    members = [MemberOut(**m.model_dump()) for m in user_store.list_members(tid)]
    invites = [InviteOut(**i.model_dump()) for i in user_store.list_invites(tid)]
    return UsersListOut(members=members, invites=invites)


@router.post("/usuarios/convidar", response_model=InviteOut, status_code=201)
async def convidar(
    body: InviteBody,
    request: Request,
    background_tasks: BackgroundTasks,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role("admin")),
):
    if body.papel not in VALID_ROLES:
        raise HTTPException(400, f"papel inválido: {body.papel}")
    tid = _tenant(request)
    invite = user_store.create_invite(tid, body.email, body.papel)
    invite_url = f"{_FRONTEND_URL}/config/aceitar-convite?token={invite.token}"
    background_tasks.add_task(send_invite_email, body.email, invite_url, tid)
    return InviteOut(**invite.model_dump())


@router.post("/usuarios/aceitar-convite", response_model=MemberOut)
async def aceitar_convite(
    body: dict,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
):
    token = body.get("token", "")
    invite = user_store.get_invite_by_token(token)
    if invite is None or invite.is_expired():
        raise HTTPException(400, "convite inválido ou expirado")
    if invite.is_accepted():
        raise HTTPException(400, "convite já utilizado")
    user_store.accept_invite(token)
    uid = body.get("user_uid", token[:16])
    member = user_store.create_member(
        invite.tenant_id, uid, invite.email, invite.papel
    )
    return MemberOut(**member.model_dump())


@router.delete("/usuarios/{member_id}", status_code=204)
async def revogar_membro(
    member_id: str,
    request: Request,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role("admin")),
):
    tid = _tenant(request)
    result = user_store.revoke_member(tid, member_id)
    if result is None:
        raise HTTPException(404, "membro não encontrado")


@router.patch("/usuarios/{member_id}/papel", response_model=MemberOut)
async def alterar_papel(
    member_id: str,
    body: PapelBody,
    request: Request,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role("admin")),
):
    if body.papel not in VALID_ROLES:
        raise HTTPException(400, f"papel inválido: {body.papel}")
    tid = _tenant(request)
    result = user_store.change_papel(tid, member_id, body.papel)
    if result is None:
        raise HTTPException(404, "membro não encontrado")
    return MemberOut(**result.model_dump())


# ── notificações ──────────────────────────────────────────────────────────────


class NotifPrefsOut(BaseModel):
    email_enabled: bool
    whatsapp_enabled: bool
    whatsapp_number: str | None = None
    tipos_habilitados: list[str]


class NotifPrefsPatch(BaseModel):
    email_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    whatsapp_number: str | None = None
    tipos_habilitados: list[str] | None = None


@router.get("/notificacoes", response_model=NotifPrefsOut)
async def get_notificacoes(
    request: Request,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role()),
):
    tid = _tenant(request)
    prefs = user_store.get_notif_prefs(tid)
    return NotifPrefsOut(**prefs.model_dump(exclude={"tenant_id"}))


@router.patch("/notificacoes", response_model=NotifPrefsOut)
async def patch_notificacoes(
    body: NotifPrefsPatch,
    request: Request,
    user_store: TenantUserStore = Depends(get_tenant_user_store),
    _auth=Depends(require_user_role()),
):
    tid = _tenant(request)
    updated = user_store.update_notif_prefs(tid, **body.model_dump(exclude_none=True))
    return NotifPrefsOut(**updated.model_dump(exclude={"tenant_id"}))


# ── dados (LGPD) ──────────────────────────────────────────────────────────────


@router.get("/dados/export")
async def export_dados(
    request: Request,
    store=Depends(get_store),
    contract_store=Depends(get_contract_store),
    alert_store=Depends(get_alert_store),
    _auth=Depends(require_user_role("admin")),
):
    tid = _tenant(request)
    runs_raw = await store.list_all()
    runs = [r.model_dump() if hasattr(r, "model_dump") else r for r in runs_raw]
    contracts_raw = await contract_store.list()
    contracts = [c.model_dump() if hasattr(c, "model_dump") else c for c in contracts_raw]
    alerts_raw = await alert_store.query(tenant_id=tid)
    alerts = [a.model_dump() if hasattr(a, "model_dump") else a for a in alerts_raw]
    return JSONResponse(
        content={"tenant_id": tid, "runs": runs, "contracts": contracts, "alerts": alerts}
    )


@router.delete("/dados", status_code=202)
async def solicitar_exclusao(
    request: Request,
    _auth=Depends(require_user_role("admin")),
):
    tid = _tenant(request)
    return {
        "status": "solicitado",
        "tenant_id": tid,
        "mensagem": "Solicitação recebida. Processamento em até 30 dias (LGPD Art. 18).",
    }
