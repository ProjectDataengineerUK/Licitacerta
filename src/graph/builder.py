from __future__ import annotations

from src.graph.supervisor import build_supervisor


def build_graph(checkpointer=None):
    return build_supervisor(checkpointer=checkpointer)
