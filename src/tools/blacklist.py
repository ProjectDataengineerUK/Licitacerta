from __future__ import annotations

from datetime import datetime

import httpx

from src.schemas.results import BlacklistResult

CGU_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
TIMEOUT = 5.0

_ENDPOINTS = {
    "ceis": "ceis",
    "cnep": "cnep",
    "cepim": "cepim",
}


def _clean_cnpj(cnpj: str) -> str:
    return cnpj.replace(".", "").replace("/", "").replace("-", "")


def check_blacklist(cnpj: str, api_key: str) -> BlacklistResult:
    """Consulta CEIS, CNEP e CEPIM. Retorna resultado sem nenhuma chamada a LLM."""
    headers = {"chave-api": api_key}
    cnpj_clean = _clean_cnpj(cnpj)

    results: dict[str, bool] = {}
    with httpx.Client(timeout=TIMEOUT) as client:
        for key, endpoint in _ENDPOINTS.items():
            r = client.get(
                f"{CGU_BASE}/{endpoint}",
                params={"cnpjSancionado": cnpj_clean, "pagina": 1},
                headers=headers,
            )
            r.raise_for_status()
            results[key] = len(r.json()) > 0

    return BlacklistResult(
        ceis_blocked=results["ceis"],
        cnep_blocked=results["cnep"],
        cepim_blocked=results["cepim"],
        any_blocked=any(results.values()),
        checked_at=datetime.utcnow(),
    )
