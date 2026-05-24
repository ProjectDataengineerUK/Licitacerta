from __future__ import annotations

from fastapi import Request

from src.api.pncp_client import PNCPClient
from src.api.store import RunStore
from src.api.watch_store import WatchStore


def get_store(request: Request) -> RunStore:
    return request.app.state.store


def get_graph(request: Request):
    return request.app.state.graph


def get_watch_store(request: Request) -> WatchStore:
    return request.app.state.watch_store


def get_pncp_client(request: Request) -> PNCPClient:
    return request.app.state.pncp_client
