from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

STATUS_VALIDA = "valida"
STATUS_VENCIDA = "vencida"
STATUS_VENCE_EM_BREVE = "vence_em_breve"
STATUS_NAO_VERIFICADA = "nao_verificada"

TIPOS_VALIDOS = ("CND_FEDERAL", "FGTS", "TRABALHISTA", "ESTADUAL_SEFAZ", "MUNICIPAL_ISSQN")

JANELA_VENCE_EM_BREVE_DIAS = 30
MARCOS_ALERTA = (30, 15, 7, 1)


def calculate_status(validade: date | None, *, hoje: date | None = None) -> str:
    if validade is None:
        return STATUS_NAO_VERIFICADA
    today = hoje or date.today()
    if validade < today:
        return STATUS_VENCIDA
    if validade < today + timedelta(days=JANELA_VENCE_EM_BREVE_DIAS):
        return STATUS_VENCE_EM_BREVE
    return STATUS_VALIDA


@dataclass(frozen=True)
class AlertaDecision:
    deve_alertar: bool
    dias_restantes: int | None
    marco: int | None
    severidade: str


def check_alertas(
    validade: date | None,
    ultimo_alerta: date | None,
    *,
    hoje: date | None = None,
) -> AlertaDecision:
    today = hoje or date.today()
    if validade is None:
        return AlertaDecision(False, None, None, "info")

    dias = (validade - today).days

    if ultimo_alerta == today:
        return AlertaDecision(False, dias, None, "info")

    if dias < 0:
        return AlertaDecision(True, dias, None, "critical")

    marco = next((m for m in sorted(MARCOS_ALERTA) if dias <= m), None)
    if marco is None:
        return AlertaDecision(False, dias, None, "info")

    severidade = "critical" if marco <= 1 else ("warning" if marco <= 7 else "info")
    return AlertaDecision(True, dias, marco, severidade)


async def listar(conn, tenant_id: str) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, tenant_id, cnpj, tipo, validade, status,
                  url_documento, verificado_em, ultimo_alerta, created_at
           FROM certidoes WHERE tenant_id = $1 ORDER BY validade ASC NULLS LAST""",
        tenant_id,
    )
    return [dict(r) for r in rows]


async def criar(
    conn,
    tenant_id: str,
    cnpj: str,
    tipo: str,
    validade: date | None,
    url_documento: str | None = None,
) -> dict:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo}")
    cid = uuid.uuid4()
    status = calculate_status(validade)
    row = await conn.fetchrow(
        """INSERT INTO certidoes
               (id, tenant_id, cnpj, tipo, validade, status, url_documento, verificado_em)
           VALUES ($1,$2,$3,$4,$5,$6,$7, CASE WHEN $5 IS NULL THEN NULL ELSE NOW() END)
           ON CONFLICT (tenant_id, cnpj, tipo) DO UPDATE
               SET validade = EXCLUDED.validade,
                   status = EXCLUDED.status,
                   url_documento = EXCLUDED.url_documento,
                   verificado_em = EXCLUDED.verificado_em
           RETURNING id, tenant_id, cnpj, tipo, validade, status,
                     url_documento, verificado_em, ultimo_alerta, created_at""",
        cid,
        tenant_id,
        cnpj,
        tipo,
        validade,
        status,
        url_documento,
    )
    return dict(row)


async def atualizar(
    conn,
    tenant_id: str,
    certidao_id,
    validade: date | None,
    url_documento: str | None = None,
) -> dict | None:
    status = calculate_status(validade)
    row = await conn.fetchrow(
        """UPDATE certidoes
              SET validade = $3,
                  status = $4,
                  url_documento = COALESCE($5, url_documento),
                  verificado_em = CASE WHEN $3 IS NULL THEN verificado_em ELSE NOW() END,
                  ultimo_alerta = NULL
            WHERE tenant_id = $1 AND id = $2
        RETURNING id, tenant_id, cnpj, tipo, validade, status,
                  url_documento, verificado_em, ultimo_alerta, created_at""",
        tenant_id,
        certidao_id,
        validade,
        status,
        url_documento,
    )
    return dict(row) if row else None


async def marcar_alertado(conn, certidao_id, hoje: date | None = None) -> None:
    await conn.execute(
        "UPDATE certidoes SET ultimo_alerta = $2 WHERE id = $1",
        certidao_id,
        hoje or date.today(),
    )
