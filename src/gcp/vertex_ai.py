from __future__ import annotations

import os
from typing import Any, Type

from pydantic import BaseModel


class VertexAILLM:
    def __init__(self, model: Any) -> None:
        self._model = model

    @classmethod
    def from_env(cls, model_id: str, temperature: float = 0.0) -> VertexAILLM:
        from langchain_google_vertexai import ChatVertexAI  # lazy import

        project = os.environ["GCP_PROJECT_ID"]
        location = os.environ.get("GCP_REGION", "southamerica-east1")
        model = ChatVertexAI(
            model_name=model_id,
            project=project,
            location=location,
            temperature=temperature,
        )
        return cls(model)

    def with_structured_output(self, schema: Type[BaseModel]) -> Any:
        return self._model.with_structured_output(schema)

    def invoke(self, messages: list) -> Any:
        return self._model.invoke(messages)

    async def ainvoke(self, messages: list) -> Any:
        return await self._model.ainvoke(messages)


class VertexAIEmbeddings:
    def __init__(self, model: Any) -> None:
        self._model = model

    @classmethod
    def from_env(cls, model_id: str = "text-multilingual-embedding-002") -> VertexAIEmbeddings:
        from langchain_google_vertexai import VertexAIEmbeddings as _Embeddings  # lazy import

        project = os.environ["GCP_PROJECT_ID"]
        location = os.environ.get("GCP_REGION", "southamerica-east1")
        model = _Embeddings(model_name=model_id, project=project, location=location)
        return cls(model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._model.aembed_documents(texts)
