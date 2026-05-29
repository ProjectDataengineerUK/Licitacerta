from __future__ import annotations

import httpx
import pytest
import respx

from src.api.pncp_client import PNCPClient

_PCA_BASE = "https://pncp.gov.br/api/pncp/v1"


@pytest.mark.asyncio
async def test_fetch_pca_items_returns_list():
    with respx.mock:
        respx.get(f"{_PCA_BASE}/orgaos/12345678000195/planosContratacoes/itens").mock(
            return_value=httpx.Response(200, json={"data": [
                {"descricaoItem": "Suporte TI", "valorEstimado": 50000.0, "numeroItem": "001"}
            ]})
        )
        async with PNCPClient() as pncp:
            items = await pncp.fetch_pca_items("12345678000195", 2026)
    assert len(items) == 1
    assert items[0]["descricaoItem"] == "Suporte TI"


@pytest.mark.asyncio
async def test_fetch_pca_items_404_returns_empty():
    with respx.mock:
        respx.get(f"{_PCA_BASE}/orgaos/99999999000199/planosContratacoes/itens").mock(
            return_value=httpx.Response(404)
        )
        async with PNCPClient() as pncp:
            items = await pncp.fetch_pca_items("99999999000199", 2026)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_pca_items_network_error_returns_empty():
    with respx.mock:
        respx.get(f"{_PCA_BASE}/orgaos/12345678000195/planosContratacoes/itens").mock(
            side_effect=httpx.ConnectError("timeout")
        )
        async with PNCPClient() as pncp:
            items = await pncp.fetch_pca_items("12345678000195", 2026)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_orgs_with_pca_returns_list():
    with respx.mock:
        respx.get(f"{_PCA_BASE}/planosContratacoes").mock(
            return_value=httpx.Response(200, json={"data": [
                {"cnpjOrgao": "12345678000195", "nomeOrgao": "ANATEL"}
            ]})
        )
        async with PNCPClient() as pncp:
            orgs = await pncp.fetch_orgs_with_pca(2026)
    assert len(orgs) == 1
    assert orgs[0]["cnpjOrgao"] == "12345678000195"


@pytest.mark.asyncio
async def test_fetch_orgs_error_returns_empty():
    with respx.mock:
        respx.get(f"{_PCA_BASE}/planosContratacoes").mock(
            return_value=httpx.Response(500)
        )
        async with PNCPClient() as pncp:
            orgs = await pncp.fetch_orgs_with_pca(2026)
    assert orgs == []
