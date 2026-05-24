from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

RECEITAWS_BASE = "https://receitaws.com.br/v1/cnpj"
TIMEOUT = 5.0


def _clean_cnpj(cnpj: str) -> str:
    return cnpj.replace(".", "").replace("/", "").replace("-", "")


def fetch_company(cnpj: str) -> dict[str, Any]:
    """
    Consulta dados cadastrais de empresa na Receita Federal via ReceitaWS.
    Retorna dict com situação, razão social, atividades, etc.
    """
    cnpj_clean = _clean_cnpj(cnpj)
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{RECEITAWS_BASE}/{cnpj_clean}")
        r.raise_for_status()
        data = r.json()

    if data.get("status") == "ERROR":
        raise ValueError(f"CNPJ inválido ou não encontrado: {data.get('message', '')}")

    return data


def is_active(cnpj: str) -> bool:
    """Retorna True se a empresa está ativa na Receita Federal."""
    data = fetch_company(cnpj)
    return str(data.get("situacao", "")).upper() == "ATIVA"
