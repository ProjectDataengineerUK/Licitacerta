from src.graph.builder import build_graph


def test_at001_import_build_graph():
    from src.graph import builder

    assert hasattr(builder, "build_graph")
    assert callable(builder.build_graph)


def test_at002_build_graph_returns_compiled_graph():
    graph = build_graph()

    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")


def test_at002_build_graph_accepts_checkpointer():
    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(checkpointer=MemorySaver())

    assert hasattr(graph, "invoke")


def test_at003_agents_worker_imports_without_crash():
    import src.workers.agents_worker as worker

    assert callable(worker.handle)
