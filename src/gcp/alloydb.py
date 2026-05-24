from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any


def create_alloydb_engine(instance_uri: str, db: str) -> Any:
    """
    Create an async SQLAlchemy engine using AlloyDB Connector (IAM auth).
    Falls back to plain asyncpg DSN if instance_uri looks like a DSN (for tests/local).
    """
    from sqlalchemy.ext.asyncio import create_async_engine  # lazy

    if instance_uri.startswith("postgresql"):
        return create_async_engine(instance_uri, pool_size=5, max_overflow=10)

    from google.cloud.alloydb.connector import AsyncConnector  # lazy

    connector = AsyncConnector()

    async def _getconn():
        return await connector.connect(instance_uri, "asyncpg", db=db, enable_iam_auth=True)

    return create_async_engine(
        "postgresql+asyncpg://",
        async_creator=_getconn,
        pool_size=5,
        max_overflow=10,
    )


def create_session_factory(engine: Any) -> Any:
    from sqlalchemy.ext.asyncio import async_sessionmaker  # lazy

    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def tenant_session(
    session_factory: Any,
    tenant_id: str,
) -> AsyncGenerator[Any, None]:
    from sqlalchemy import text  # lazy

    async with session_factory() as session:
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id}
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
