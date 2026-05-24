from __future__ import annotations

import os
from typing import Any


def get_langfuse_handler(run_id: str) -> Any | None:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        return None
    try:
        from langfuse.callback import CallbackHandler

        return CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            session_id=run_id,
            trace_name=f"licitacerta-run-{run_id}",
        )
    except ImportError:
        return None


def setup_otel(service_name: str = "licitacerta-api") -> None:
    """Configure OpenTelemetry with Cloud Trace exporter when running on GCP."""
    if not os.environ.get("GCP_PROJECT_ID"):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
        trace.set_tracer_provider(provider)
    except ImportError:
        pass
