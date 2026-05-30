"""PCA endpoints — deterministic via injected MockTransport.

We inject an httpx ``MockTransport`` into ``PNCPClient`` instead of relying on
respx's global httpx patching, which is sensitive to test-collection order and
network availability (in suite order on CI, an unpatched call would hit the
network, fail, and the client's broad ``except`` would mask it as an empty
list). This mirrors the pattern used in ``test_portal_v2.py``.
"""
from __future__ import annotations

import json

import httpx
import pytest
from httpx import AsyncClient, MockTransport

from src.api.pncp_client import PNCPClient


def _transport(routes) -> MockTransport:
    """Build a MockTransport dispatching on URL path suffix.

    ``routes`` maps a path suffix to an httpx.Response (or a callable taking the
    request and returning a Response).
    """

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for suffix, response in routes.items():
            if path.endswith(suffix):
                return response(request) if callable(response) else response
        return httpx.Response(404)

    return MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_pca_items_returns_list():
    transport = _transport({
        "/orgaos/12345678000195/planosContratacoes/itens": httpx.Response(
            200,
            content=json.dumps({"data": [
                {"descricaoItem": "Suporte TI", "valorEstimado": 50000.0, "numeroItem": "001"}
            ]}).encode(),
        ),
    })
    async with PNCPClient(client=AsyncClient(transport=transport)) as pncp:
        items = await pncp.fetch_pca_items("12345678000195", 2026)
    assert len(items) == 1
    assert items[0]["descricaoItem"] == "Suporte TI"


@pytest.mark.asyncio
async def test_fetch_pca_items_404_returns_empty():
    transport = _transport({
        "/orgaos/99999999000199/planosContratacoes/itens": httpx.Response(404),
    })
    async with PNCPClient(client=AsyncClient(transport=transport)) as pncp:
        items = await pncp.fetch_pca_items("99999999000199", 2026)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_pca_items_network_error_returns_empty():
    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("timeout")

    transport = _transport({
        "/orgaos/12345678000195/planosContratacoes/itens": _boom,
    })
    async with PNCPClient(client=AsyncClient(transport=transport)) as pncp:
        items = await pncp.fetch_pca_items("12345678000195", 2026)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_orgs_with_pca_returns_list():
    transport = _transport({
        "/planosContratacoes": httpx.Response(
            200,
            content=json.dumps({"data": [
                {"cnpjOrgao": "12345678000195", "nomeOrgao": "ANATEL"}
            ]}).encode(),
        ),
    })
    async with PNCPClient(client=AsyncClient(transport=transport)) as pncp:
        orgs = await pncp.fetch_orgs_with_pca(2026)
    assert len(orgs) == 1
    assert orgs[0]["cnpjOrgao"] == "12345678000195"


@pytest.mark.asyncio
async def test_fetch_orgs_error_returns_empty():
    transport = _transport({
        "/planosContratacoes": httpx.Response(500),
    })
    async with PNCPClient(client=AsyncClient(transport=transport)) as pncp:
        orgs = await pncp.fetch_orgs_with_pca(2026)
    assert orgs == []
