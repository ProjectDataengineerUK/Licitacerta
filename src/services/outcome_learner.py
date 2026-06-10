from __future__ import annotations
from src.agents.model_router import get_llm, ModelTier

_PROMPT = """Você é um analista de licitações. Analise:
- Score BidNoBid: {score:.2f}
- Resultado: {resultado}
- Preço proposto: {preco_proposto}
- Preço vencedor: {preco_vencedor}

Em 1-2 frases (máx 150 tokens), aponte o insight principal sobre a qualidade desta previsão."""


async def gerar_insight(
    score: float | None,
    resultado: str,
    preco_proposto: float | None,
    preco_vencedor: float | None,
) -> str | None:
    if score is None:
        return None
    try:
        llm = get_llm(ModelTier.CLASSIFY)
        prompt = _PROMPT.format(
            score=score,
            resultado=resultado,
            preco_proposto=preco_proposto or "não informado",
            preco_vencedor=preco_vencedor or "não informado",
        )
        resp = await llm.ainvoke(prompt)
        return resp.content.strip()
    except Exception:
        return None
