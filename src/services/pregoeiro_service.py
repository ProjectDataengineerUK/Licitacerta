"""PregoeicoService — lookup + score formula for pregoeiro profiles."""
from __future__ import annotations

import logging
import unicodedata
from typing import Any

from src.schemas.pregoeiro import EmpresaFrequente, PregoeiroPerfil

logger = logging.getLogger(__name__)

_MIN_SESSIONS_FOR_SCORE = 10
_CONFIANCA_LABEL_THRESHOLD = 0.4


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _calc_indice(
    taxa_aceitacao: float | None,
    taxa_desclassificacao: float | None,
    previsibilidade: float | None,
    tempo_medio: float | None,
    media_desclassificacao: float = 15.0,
) -> float:
    score = 50.0
    if taxa_aceitacao is not None:
        score += (taxa_aceitacao - 50) * 0.3
    if taxa_desclassificacao is not None:
        score -= max(0, taxa_desclassificacao - media_desclassificacao) * 0.4
    if previsibilidade is not None:
        score += previsibilidade * 20
    if tempo_medio is not None:
        score -= max(0, tempo_medio - 4) * 2
    return max(0.0, min(100.0, score))


def _build_alertas(
    taxa_impugnacao: float | None,
    taxa_desclassificacao: float | None,
    tempo_medio: float | None,
    media_desclassificacao: float = 15.0,
) -> list[str]:
    alertas: list[str] = []
    if taxa_impugnacao is not None and taxa_impugnacao >= 80:
        alertas.append("Impugnações geralmente aceitas por este pregoeiro (taxa ≥80%)")
    if taxa_desclassificacao is not None and taxa_desclassificacao > media_desclassificacao * 1.5:
        alertas.append(f"Taxa de desclassificação acima da média ({taxa_desclassificacao:.0f}% vs {media_desclassificacao:.0f}% média)")
    if tempo_medio is not None and tempo_medio > 8:
        alertas.append(f"Sessões longas em média ({tempo_medio:.1f}h)")
    return alertas


class PregoeicoService:
    def __init__(self, db: Any) -> None:
        self._db = db

    async def lookup(self, nome: str, orgao_cnpj: str) -> PregoeiroPerfil:
        nome_norm = _normalize(nome)
        try:
            row = await self._db.fetchrow(
                "SELECT * FROM pregoeiro_profiles WHERE nome_normalizado = $1 AND orgao_cnpj = $2",
                nome_norm,
                orgao_cnpj,
            )
        except Exception as exc:
            logger.warning("pregoeiro_service.lookup DB error: %s", exc)
            row = None

        if not row:
            return PregoeiroPerfil(
                nome=nome,
                orgao_cnpj=orgao_cnpj,
                total_sessoes=0,
                confianca_pct=0.0,
                label_confianca="Sem dados",
            )

        total = row["total_sessoes"] or 0
        confianca = min(1.0, total / _MIN_SESSIONS_FOR_SCORE)
        taxa_imp = row["taxa_aceitacao_impugnacao_pct"]
        taxa_desc = row["taxa_desclassificacao_pct"]
        tempo = row["tempo_medio_sessao_horas"]
        prev = row["previsibilidade"]

        indice = None
        if confianca >= _CONFIANCA_LABEL_THRESHOLD:
            indice = _calc_indice(taxa_imp, taxa_desc, prev, tempo)

        label = (
            f"{total} sessões analisadas"
            if confianca >= _CONFIANCA_LABEL_THRESHOLD
            else f"Perfil em formação ({total} sessões)"
        )

        import json
        emps_raw = row["empresas_frequentes_vencedoras"]
        if isinstance(emps_raw, str):
            emps_raw = json.loads(emps_raw)
        empresas = [EmpresaFrequente(**e) for e in (emps_raw or [])]

        return PregoeiroPerfil(
            nome=row["nome"],
            orgao_cnpj=orgao_cnpj,
            orgao_nome=row.get("orgao_nome"),
            total_sessoes=total,
            indice_reputacao=indice,
            confianca_pct=confianca,
            label_confianca=label,
            taxa_aceitacao_impugnacao_pct=taxa_imp,
            taxa_desclassificacao_pct=taxa_desc,
            tempo_medio_sessao_horas=tempo,
            previsibilidade=prev,
            clausulas_frequentes=json.loads(row["clausulas_frequentes"] or "[]"),
            tipos_desclassificacao=json.loads(row["tipos_desclassificacao"] or "[]"),
            empresas_frequentes_vencedoras=empresas,
            alertas=_build_alertas(taxa_imp, taxa_desc, tempo),
        )
