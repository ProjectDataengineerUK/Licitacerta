from __future__ import annotations

import math
from datetime import date

import httpx

_BASE = "https://pncp.gov.br/api/consulta/v1"

# Modalidades mais relevantes para PMEs de TI/serviços
# 6=Pregão Eletrônico, 4=Concorrência Eletrônica, 8=Dispensa, 9=Inexigibilidade
_MODALIDADES = [6, 4, 8, 9]


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
        modalidade: int,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict]:
        assert self._client is not None, "PNCPClient must be used as async context manager"
        resp = await self._client.get(
            f"{_BASE}/contratacoes/publicacao",
            params={
                "dataInicial": data_inicial.isoformat(),
                "dataFinal": data_final.isoformat(),
                "codigoModalidadeContratacao": modalidade,
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
        results: list[dict] = []
        seen: set[str] = set()

        def _add(editais: list[dict]) -> None:
            for edital in editais:
                pncp_id = edital.get("numeroControlePNCP")
                if pncp_id is not None and pncp_id in seen:
                    continue
                if pncp_id is not None:
                    seen.add(pncp_id)
                results.append(edital)

        for modalidade in _MODALIDADES:
            try:
                resp = await self._client.get(
                    f"{_BASE}/contratacoes/publicacao",
                    params={
                        "dataInicial": data_inicial.isoformat(),
                        "dataFinal": data_final.isoformat(),
                        "codigoModalidadeContratacao": modalidade,
                        "pagina": 1,
                        "tamanhoPagina": page_size,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
                _add(payload.get("data", []))

                total = payload.get("totalRegistros", 0)
                total_pages = math.ceil(total / page_size) if total > page_size else 1

                for page in range(2, total_pages + 1):
                    try:
                        page_results = await self.search_publicacoes(
                            data_inicial, data_final, modalidade, page, page_size
                        )
                        _add(page_results)
                    except Exception:
                        break
            except Exception:
                continue

        return results

    async def fetch_pca_items(
        self,
        orgao_cnpj: str,
        ano: int,
        page_size: int = 100,
    ) -> list[dict]:
        assert self._client is not None
        _base = "https://pncp.gov.br/api/pncp/v1"
        results: list[dict] = []
        page = 1
        while True:
            try:
                resp = await self._client.get(
                    f"{_base}/orgaos/{orgao_cnpj}/planosContratacoes/itens",
                    params={"ano": ano, "pagina": page, "tamanhoPagina": page_size},
                    timeout=20.0,
                )
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                payload = resp.json()
                items = payload.get("data", [])
                if not items:
                    break
                results.extend(items)
                if len(items) < page_size:
                    break
                page += 1
            except Exception:
                break
        return results

    async def fetch_orgs_with_pca(self, ano: int, page_size: int = 50) -> list[dict]:
        assert self._client is not None
        _base = "https://pncp.gov.br/api/pncp/v1"
        try:
            resp = await self._client.get(
                f"{_base}/planosContratacoes",
                params={"ano": ano, "pagina": 1, "tamanhoPagina": page_size},
                timeout=20.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception:
            return []
