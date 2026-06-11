"""PERSISTENCIA_STORES — implementações AlloyDB dos stores de interface async.

Mesma assinatura pública dos stores in-memory (contract/billing/alert/watch).
SQL direto via asyncpg (padrão certidao_service); linha = JSONB `data` +
colunas promovidas para filtros. Sem cache: consistente multi-instância.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.api.alert_store import Alert, AlertCreate, NotificationPreferences
from src.api.billing_store import TenantBilling
from src.api.contract_store import (
    Contract,
    ContractCreate,
    ContractPatch,
    Convocacao,
    ConvocacaoCreate,
    Empenho,
    EmpenhoCreate,
    EmpenhoPatch,
)
from src.api.watch_store import WatchConfig, WatchedEdital


def _watch_config_json(cfg: WatchConfig) -> str:
    d = asdict(cfg)
    d["id"] = str(cfg.id)
    d["created_at"] = cfg.created_at.isoformat()
    d["last_polled_at"] = cfg.last_polled_at.isoformat() if cfg.last_polled_at else None
    return json.dumps(d)


def _watch_config_from(data: str) -> WatchConfig:
    d = json.loads(data)
    return WatchConfig(
        id=UUID(d["id"]),
        keywords=d["keywords"],
        cnpj=d["cnpj"],
        active=d.get("active", True),
        last_polled_at=datetime.fromisoformat(d["last_polled_at"]) if d.get("last_polled_at") else None,
        created_at=datetime.fromisoformat(d["created_at"]),
    )


class AlloyDBContractStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def _save(self, conn: Any, c: Contract) -> None:
        await conn.execute(
            "INSERT INTO contracts (id, tenant_id, status, data_inicio, data_vencimento, data) "
            "VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (id) DO UPDATE SET "
            "tenant_id=EXCLUDED.tenant_id, status=EXCLUDED.status, data_inicio=EXCLUDED.data_inicio, "
            "data_vencimento=EXCLUDED.data_vencimento, data=EXCLUDED.data, updated_at=now()",
            c.id, c.tenant_id, c.status, c.data_inicio, c.data_vencimento, c.model_dump_json(),
        )

    async def create(self, body: ContractCreate, tenant_id: str | None = None) -> Contract:
        contract = Contract(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            valor_atual_brl=body.valor_original_brl,
            **body.model_dump(),
        )
        async with self._pool.acquire() as conn:
            await self._save(conn, contract)
        return contract

    async def get(self, cid: str) -> Contract | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM contracts WHERE id=$1", cid)
        return Contract.model_validate_json(row["data"]) if row else None

    async def list(self, status: str | None = None) -> list[Contract]:
        q = "SELECT data FROM contracts"
        args: list[Any] = []
        if status:
            q += " WHERE status=$1"
            args.append(status)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(q, *args)
        return [Contract.model_validate_json(r["data"]) for r in rows]

    async def _modify(self, cid: str, fn: Any) -> Any:
        """Read-modify-write com lock de linha (FOR UPDATE)."""
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow("SELECT data FROM contracts WHERE id=$1 FOR UPDATE", cid)
            if row is None:
                return None
            c = Contract.model_validate_json(row["data"])
            result = fn(c)
            if result is None:
                return None
            await self._save(conn, c)
            return result

    async def patch(self, cid: str, body: ContractPatch) -> Contract | None:
        def _apply(c: Contract) -> Contract:
            for key, value in body.model_dump(exclude_none=True).items():
                setattr(c, key, value)
            return c
        return await self._modify(cid, _apply)

    async def delete(self, cid: str) -> bool:
        def _apply(c: Contract) -> Contract:
            c.status = "encerrado"
            return c
        return await self._modify(cid, _apply) is not None

    async def add_empenho(self, cid: str, body: EmpenhoCreate) -> Empenho | None:
        emp = Empenho(id=str(uuid.uuid4()), **body.model_dump())

        def _apply(c: Contract) -> Empenho:
            c.empenhos.append(emp)
            return emp
        return await self._modify(cid, _apply)

    async def patch_empenho(self, cid: str, eid: str, body: EmpenhoPatch) -> Empenho | None:
        def _apply(c: Contract) -> Empenho | None:
            emp = next((e for e in c.empenhos if e.id == eid), None)
            if emp is None:
                return None
            for key, value in body.model_dump(exclude_none=True).items():
                setattr(emp, key, value)
            return emp
        return await self._modify(cid, _apply)

    async def add_convocacao(self, cid: str, body: ConvocacaoCreate) -> Convocacao | None:
        conv = Convocacao(id=str(uuid.uuid4()), **body.model_dump())

        def _apply(c: Contract) -> Convocacao:
            c.convocacoes.append(conv)
            return conv
        return await self._modify(cid, _apply)


class AlloyDBBillingStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def set(self, billing: TenantBilling) -> TenantBilling:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO tenant_billing (tenant_id, stripe_customer_id, stripe_subscription_id, data) "
                "VALUES ($1,$2,$3,$4) ON CONFLICT (tenant_id) DO UPDATE SET "
                "stripe_customer_id=EXCLUDED.stripe_customer_id, "
                "stripe_subscription_id=EXCLUDED.stripe_subscription_id, "
                "data=EXCLUDED.data, updated_at=now()",
                billing.tenant_id, billing.stripe_customer_id,
                billing.stripe_subscription_id, billing.model_dump_json(),
            )
        return billing

    async def _fetch_one(self, where: str, *args: Any) -> TenantBilling | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT data FROM tenant_billing WHERE {where}", *args)
        return TenantBilling.model_validate_json(row["data"]) if row else None

    async def get(self, tenant_id: str) -> TenantBilling | None:
        return await self._fetch_one("tenant_id=$1", tenant_id)

    async def create_trial(self, tenant_id: str, trial_days: int = 7) -> TenantBilling:
        from datetime import timedelta
        billing = TenantBilling(
            tenant_id=tenant_id,
            plan="trial",
            subscription_status="trial",
            trial_ends_at=datetime.now() + timedelta(days=trial_days),
        )
        return await self.set(billing)

    async def get_or_create_trial(self, tenant_id: str, trial_days: int = 7) -> TenantBilling:
        existing = await self.get(tenant_id)
        if existing is not None:
            return existing
        return await self.create_trial(tenant_id, trial_days)

    async def increment_usage(self, tenant_id: str) -> None:
        b = await self.get(tenant_id)
        if b is not None:
            b.usage_analises_mes += 1
            await self.set(b)

    async def get_by_subscription_id(self, subscription_id: str) -> TenantBilling | None:
        return await self._fetch_one("stripe_subscription_id=$1", subscription_id)

    async def get_by_customer_id(self, customer_id: str) -> TenantBilling | None:
        return await self._fetch_one("stripe_customer_id=$1", customer_id)

    async def all(self) -> list[TenantBilling]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM tenant_billing")
        return [TenantBilling.model_validate_json(r["data"]) for r in rows]


class AlloyDBAlertStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def create(self, body: AlertCreate) -> Alert:
        alert = Alert(id=str(uuid.uuid4()), **body.model_dump())
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO alerts (id, tenant_id, lido, severidade, created_at, data) "
                "VALUES ($1,$2,$3,$4,$5,$6)",
                alert.id, alert.tenant_id, alert.lido, alert.severidade,
                alert.created_at, alert.model_dump_json(),
            )
        return alert

    async def get(self, alert_id: str) -> Alert | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM alerts WHERE id=$1", alert_id)
        return Alert.model_validate_json(row["data"]) if row else None

    async def query(
        self,
        tenant_id: str | None = None,
        lido: bool | None = None,
        severidade: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Alert]:
        clauses: list[str] = []
        args: list[Any] = []
        for col, val in (("tenant_id", tenant_id), ("lido", lido), ("severidade", severidade)):
            if val is not None:
                args.append(val)
                clauses.append(f"{col}=${len(args)}")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        args += [page_size, (page - 1) * page_size]
        q = (
            f"SELECT data FROM alerts{where} ORDER BY created_at DESC "
            f"LIMIT ${len(args) - 1} OFFSET ${len(args)}"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(q, *args)
        return [Alert.model_validate_json(r["data"]) for r in rows]

    async def mark_read(self, ids: list[str]) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE alerts SET lido=TRUE, data = jsonb_set(data, '{lido}', 'true') "
                "WHERE id = ANY($1) AND lido=FALSE",
                ids,
            )
        return int(result.split()[-1])

    async def get_prefs(self, tenant_id: str) -> NotificationPreferences:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM notification_prefs WHERE tenant_id=$1", tenant_id
            )
        if row:
            return NotificationPreferences.model_validate_json(row["data"])
        return NotificationPreferences(tenant_id=tenant_id)

    async def set_prefs(self, prefs: NotificationPreferences) -> NotificationPreferences:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO notification_prefs (tenant_id, data) VALUES ($1,$2) "
                "ON CONFLICT (tenant_id) DO UPDATE SET data=EXCLUDED.data, updated_at=now()",
                prefs.tenant_id, prefs.model_dump_json(),
            )
        return prefs


class AlloyDBWatchStore:
    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def create_config(self, keywords: list[str], cnpj: str) -> WatchConfig:
        cfg = WatchConfig(id=uuid4(), keywords=keywords, cnpj=cnpj)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO watch_configs (id, data) VALUES ($1,$2)",
                str(cfg.id), _watch_config_json(cfg),
            )
        return cfg

    async def list_configs(self) -> list[WatchConfig]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM watch_configs")
        return [_watch_config_from(r["data"]) for r in rows]

    async def delete_config(self, config_id: UUID) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM watch_configs WHERE id=$1", str(config_id)
            )
        return result.split()[-1] != "0"

    async def is_seen(self, pncp_id: str) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM watch_seen WHERE pncp_id=$1", pncp_id)
        return row is not None

    async def record(self, pncp_id: str, watch_config_id: UUID, run_id: str) -> WatchedEdital:
        entry = WatchedEdital(
            id=uuid4(), pncp_id=pncp_id, watch_config_id=watch_config_id, run_id=run_id
        )
        d = asdict(entry)
        d["id"], d["watch_config_id"] = str(entry.id), str(entry.watch_config_id)
        d["triggered_at"] = entry.triggered_at.isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO watch_seen (pncp_id, data) VALUES ($1,$2) "
                "ON CONFLICT (pncp_id) DO NOTHING",
                pncp_id, json.dumps(d),
            )
        return entry

    async def update_polled_at(self, config_id: UUID) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                "SELECT data FROM watch_configs WHERE id=$1 FOR UPDATE", str(config_id)
            )
            if row is None:
                return
            cfg = _watch_config_from(row["data"])
            cfg.last_polled_at = datetime.utcnow()
            await conn.execute(
                "UPDATE watch_configs SET data=$2, updated_at=now() WHERE id=$1",
                str(config_id), _watch_config_json(cfg),
            )
