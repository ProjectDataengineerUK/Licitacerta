from __future__ import annotations

import math
from datetime import date

import httpx

_BASE = "https://pncp.gov.br/api/consulta/v1"


class PNCPClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> PNCPClient:
        if self._owns_client:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None

    async def search_publicacoes(
        self,
        data_inicial: date,
        data_final: date,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict]:
        assert self._client is not None, "PNCPClient must be used as async context manager"
        resp = await self._client.get(
            f"{_BASE}/contratacoes/publicacao",
            params={
                "dataInicial": data_inicial.isoformat(),
                "dataFinal": data_final.isoformat(),
                "pagina": page,
                "tamanhoPagina": page_size,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("data", [])

    async def search_publicacoes_all(
        self,
        data_inicial: date,
        data_final: date,
        page_size: int = 50,
    ) -> list[dict]:
        assert self._client is not None, "PNCPClient must be used as async context manager"
        resp = await self._client.get(
            f"{_BASE}/contratacoes/publicacao",
            params={
                "dataInicial": data_inicial.isoformat(),
                "dataFinal": data_final.isoformat(),
                "pagina": 1,
                "tamanhoPagina": page_size,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        results = list(payload.get("data", []))
        total = payload.get("totalRegistros", 0)
        total_pages = math.ceil(total / page_size) if total > page_size else 1

        for page in range(2, total_pages + 1):
            try:
                page_results = await self.search_publicacoes(
                    data_inicial, data_final, page, page_size
                )
                results.extend(page_results)
            except Exception:
                break

        return results
