"""Cloud Run Job: watch agent worker.

Scheduled via Cloud Scheduler. Polls active watch_configs,
runs the Watch agent, and emits alerts via Pub/Sub.
"""
from __future__ import annotations

import asyncio


def run() -> None:
    asyncio.run(_async_run())


async def _async_run() -> None:
    from sqlalchemy import select, text

    from src.config import settings
    from src.gcp.alloydb import create_alloydb_engine, create_session_factory
    from src.gcp.pubsub import PubSubPublisher

    engine = create_alloydb_engine(settings.alloydb_instance_uri, settings.alloydb_db)
    session_factory = create_session_factory(engine)
    publisher = PubSubPublisher.from_env()

    async with session_factory() as session:
        rows = await session.execute(
            text("SELECT id, tenant_id, portal_url, deadline_at FROM watch_configs WHERE active = true")
        )
        configs = rows.fetchall()

    for config in configs:
        watch_config_id, tenant_id, portal_url, deadline_at = config
        publisher.publish_event(
            "watch-check-requested",
            {
                "watch_config_id": str(watch_config_id),
                "tenant_id": str(tenant_id),
                "portal_url": portal_url,
            },
        )


if __name__ == "__main__":
    run()
