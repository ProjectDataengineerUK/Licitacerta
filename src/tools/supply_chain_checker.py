"""Ferramenta determinística de conformidade de supply chain.

Consulta APIs externas (Anvisa, INMETRO, CEIS, MAPA, MCT) por categoria CNAE.
Nunca bloqueia o pipeline — retorna `nao_verificado` quando API indisponível.
"""

from __future__ import annotations

import logging

import httpx

from src.schemas.supply_chain import APICheck, CheckStatus, SupplyChainCheckResult

logger = logging.getLogger(__name__)

SUPPLY_CHAIN_CHECKS: dict[str, list[str]] = {
    "material_hospitalar":    ["anvisa", "bpf", "ceis"],
    "alimentos":              ["anvisa_alimentos", "mapa", "ceis"],
    "equipamentos_eletricos": ["inmetro", "ceis"],
    "ti_hardware":            ["origem_nacional", "ceis"],
    "medicamentos":           ["anvisa_medicamentos", "bpf", "ceis"],
}

_CATEGORIA_CNAE: dict[str, list[str]] = {
    "material_hospitalar":    ["3250", "4664"],
    "alimentos":              ["1091", "1094", "4637"],
    "equipamentos_eletricos": ["2731", "4753"],
    "ti_hardware":            ["2621", "4651"],
    "medicamentos":           ["2121", "4644"],
}

_CEIS_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados/ceis"


def _detect_categoria(cnae: str | None, descricao: str) -> str | None:
    if cnae:
        prefix = cnae[:4].replace("-", "").replace(".", "")
        for cat, codes in _CATEGORIA_CNAE.items():
            if prefix in codes:
                return cat

    desc_lower = descricao.lower()
    if any(k in desc_lower for k in ("hospitalar", "medic", "cirúrg", "cirurg")):
        return "material_hospitalar"
    if any(k in desc_lower for k in ("aliment", "bebida", "nutriç")):
        return "alimentos"
    if any(k in desc_lower for k in ("notebook", "computador", "servidor", "switch", "roteador")):
        return "ti_hardware"
    if any(k in desc_lower for k in ("medicamento", "fármaco", "farmáco", "remédio")):
        return "medicamentos"
    if any(k in desc_lower for k in ("elétric", "eletrodom", "gerador")):
        return "equipamentos_eletricos"
    return None


def _build_fundamentacao(checks: list[APICheck], status: CheckStatus) -> str | None:
    if status == "aprovado":
        return "Todos os registros de conformidade verificados e aprovados."
    reprovados = [c.api for c in checks if c.status == "reprovado"]
    nao_ver = [c.api for c in checks if c.status == "nao_verificado"]
    parts = []
    if reprovados:
        parts.append(f"Reprovado em: {', '.join(reprovados)}")
    if nao_ver:
        parts.append(f"Não verificado em: {', '.join(nao_ver)}")
    return "; ".join(parts) or None


def _aggregate_status(checks: list[APICheck]) -> CheckStatus:
    statuses = {c.status for c in checks}
    if "reprovado" in statuses:
        return "reprovado"
    if "pendente_regularizacao" in statuses:
        return "pendente_regularizacao"
    if "nao_verificado" in statuses:
        return "nao_verificado"
    return "aprovado"


async def _check_ceis(cnpj: str) -> APICheck:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _CEIS_BASE,
                params={"cnpj": cnpj, "pagina": 1, "tamanhoPagina": 1},
            )
            if resp.status_code == 404:
                return APICheck(api="ceis", status="aprovado")
            resp.raise_for_status()
            data = resp.json()
            if data.get("data"):
                return APICheck(api="ceis", status="reprovado", nota="Sanção ativa no CEIS")
            return APICheck(api="ceis", status="aprovado")
    except Exception as exc:
        return APICheck(api="ceis", status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _check_anvisa(cnpj: str, produto: str, api_key: str) -> APICheck:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://consultas.anvisa.gov.br/api/produto",
                params={"empresa": cnpj, "nomeProduto": produto[:60]},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("content"):
                reg = data["content"][0]
                return APICheck(
                    api=api_key,
                    status="aprovado",
                    numero_registro=reg.get("numeroRegistro"),
                    valido_ate=reg.get("dataVencimento"),
                )
            return APICheck(api=api_key, status="pendente_regularizacao", nota="Produto não encontrado na base Anvisa")
    except Exception as exc:
        return APICheck(api=api_key, status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _check_inmetro(cnpj: str, produto: str) -> APICheck:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.inmetro.gov.br/api/produto",
                params={"empresa": cnpj, "produto": produto[:60]},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("certificado"):
                return APICheck(api="inmetro", status="aprovado", numero_registro=data["certificado"])
            return APICheck(api="inmetro", status="pendente_regularizacao", nota="Sem certificado INMETRO")
    except Exception as exc:
        return APICheck(api="inmetro", status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _check_mapa(cnpj: str, produto: str) -> APICheck:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://sistemas.agricultura.gov.br/api/sisend",
                params={"cnpj": cnpj, "produto": produto[:60]},
            )
            resp.raise_for_status()
            if resp.json().get("registro"):
                return APICheck(api="mapa", status="aprovado")
            return APICheck(api="mapa", status="pendente_regularizacao")
    except Exception as exc:
        return APICheck(api="mapa", status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _check_origem_nacional(cnpj: str) -> APICheck:
    # Placeholder: verifica se CNPJ tem natureza "nacional" no CNPJ.ws
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
            resp.raise_for_status()
            data = resp.json()
            uf = data.get("uf", "")
            if uf and uf != "EX":  # EX = exterior
                return APICheck(api="origem_nacional", status="aprovado")
            return APICheck(api="origem_nacional", status="reprovado", nota="Empresa de origem estrangeira")
    except Exception as exc:
        return APICheck(api="origem_nacional", status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _check_bpf(cnpj: str) -> APICheck:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://consultas.anvisa.gov.br/api/bpf",
                params={"cnpj": cnpj},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("certificado"):
                return APICheck(
                    api="bpf", status="aprovado",
                    numero_registro=data.get("numeroCertificado"),
                    valido_ate=data.get("dataVencimento"),
                )
            return APICheck(api="bpf", status="pendente_regularizacao", nota="Sem certificado BPF ativo")
    except Exception as exc:
        return APICheck(api="bpf", status="nao_verificado", nota=f"API indisponível: {type(exc).__name__}")


async def _call_api(api: str, cnpj: str, produto: str) -> APICheck:
    try:
        if api == "ceis":
            return await _check_ceis(cnpj)
        if api.startswith("anvisa"):
            return await _check_anvisa(cnpj, produto, api)
        if api == "inmetro":
            return await _check_inmetro(cnpj, produto)
        if api == "mapa":
            return await _check_mapa(cnpj, produto)
        if api == "origem_nacional":
            return await _check_origem_nacional(cnpj)
        if api == "bpf":
            return await _check_bpf(cnpj)
    except Exception as exc:
        logger.warning("supply_chain._call_api(%s) falhou: %s", api, exc)
    return APICheck(api=api, status="nao_verificado", nota="Verificação não implementada")


async def check(
    produto_descricao: str,
    fabricante_nome: str,
    fabricante_cnpj: str,
    segmento_cnae: str | None,
) -> SupplyChainCheckResult | None:
    categoria = _detect_categoria(segmento_cnae, produto_descricao)
    if not categoria:
        return None

    apis_needed = SUPPLY_CHAIN_CHECKS[categoria]
    api_checks: list[APICheck] = []
    for api in apis_needed:
        result = await _call_api(api, fabricante_cnpj, produto_descricao)
        api_checks.append(result)

    status_geral = _aggregate_status(api_checks)
    return SupplyChainCheckResult(
        produto_descricao=produto_descricao,
        fabricante_nome=fabricante_nome,
        fabricante_cnpj=fabricante_cnpj,
        categoria=categoria,
        checks=api_checks,
        status_geral=status_geral,
        bloqueante=status_geral == "reprovado",
        fundamentacao=_build_fundamentacao(api_checks, status_geral),
    )
