from __future__ import annotations

from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel

from src.agents.model_router import ModelTier, get_llm

T = TypeVar("T", bound=BaseModel)


def build_agent(
    tier: ModelTier,
    output_schema: Type[T],
    system_prompt: str,
    agent_name: str = "agent",
) -> Callable[[dict[str, Any]], T]:
    llm = get_llm(tier).with_structured_output(output_schema)

    def run(context: dict[str, Any]) -> T:
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer("licitacerta.agents")
            with tracer.start_as_current_span(f"agent.{agent_name}"):
                return _invoke(llm, system_prompt, context)
        except Exception:
            return _invoke(llm, system_prompt, context)

    return run


def _invoke(llm: Any, system_prompt: str, context: dict[str, Any]) -> Any:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": str(context)},
    ]
    return llm.invoke(messages)
