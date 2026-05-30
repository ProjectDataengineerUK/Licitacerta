from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agents.model_router import ModelTier, get_llm


class PCAClassification(BaseModel):
    segmento_cnae: str
    categoria: str
    confianca: float


_SYSTEM = """Classifique itens do Plano de Contratações Anual (PCA) brasileiro.
Para cada item retorne JSON com: segmento_cnae (código CNAE, ex: "6209-1"),
categoria ("servico"/"produto"/"obra"), confianca (0.0-1.0).
Exemplos:
- "suporte técnico de TI" → segmento_cnae="6209-1", categoria="servico", confianca=0.9
- "limpeza predial" → segmento_cnae="8121-4", categoria="servico", confianca=0.95
- "construção de muro" → segmento_cnae="4120-4", categoria="obra", confianca=0.85
- "material de escritório" → segmento_cnae="4761-0", categoria="produto", confianca=0.7"""

_DEFAULT = PCAClassification(segmento_cnae="0000-0", categoria="servico", confianca=0.0)


class PCAClassifierAgent:
    def __init__(self) -> None:
        self._llm = get_llm(ModelTier.CLASSIFY).with_structured_output(
            PCAClassification, include_raw=False
        )

    async def classify(self, descricao: str) -> PCAClassification:
        results = await self.classify_batch([descricao])
        return results[0]

    async def classify_batch(self, descricoes: list[str]) -> list[PCAClassification]:
        if not descricoes:
            return []
        results: list[PCAClassification] = []
        for descricao in descricoes:
            try:
                msgs = [SystemMessage(content=_SYSTEM), HumanMessage(content=descricao)]
                result = await self._llm.ainvoke(msgs)
                results.append(result if isinstance(result, PCAClassification) else _DEFAULT)
            except Exception:
                results.append(_DEFAULT)
        return results
