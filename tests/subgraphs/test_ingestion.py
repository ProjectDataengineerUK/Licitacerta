from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.graph.state import initial_state
from src.schemas.tender import PageContent


def _make_pages() -> list[PageContent]:
    return [
        PageContent(page_number=1, text="Objeto: Fornecimento de papel A4.", tables=[], is_ocr=False),
        PageContent(page_number=2, text="Habilitação jurídica.", tables=[], is_ocr=False),
    ]


@pytest.fixture()
def ingestion_graph_with_mock():
    mock_agent = MagicMock()
    mock_agent.run.return_value = _make_pages()

    with patch("src.graph.subgraphs.ingestion.ReadParseAgent", return_value=mock_agent):
        from src.graph.subgraphs.ingestion import build_ingestion_subgraph

        graph = build_ingestion_subgraph()
        yield graph, mock_agent


def test_ingestion_happy_path(ingestion_graph_with_mock):
    graph, mock_agent = ingestion_graph_with_mock
    state = initial_state("edital-001", "texto bruto do edital", "12345678000195")

    result = graph.invoke(state)

    assert result["current_step"] == "ingested"
    assert len(result["edital_pages"]) == 2
    assert result["edital_pages"][0].page_number == 1
    assert len(result["audit_log"]) == 1
    assert result["audit_log"][0].subgraph == "ingestion"
    assert result["audit_log"][0].agent == "read_parse"
    assert result["errors"] == []


def test_ingestion_captures_agent_error(ingestion_graph_with_mock):
    graph, mock_agent = ingestion_graph_with_mock
    mock_agent.run.side_effect = ValueError("PDF corrompido")

    state = initial_state("edital-002", "pdf corrompido", "12345678000195")
    result = graph.invoke(state)

    assert result["current_step"] == "ingestion_failed"
    assert len(result["errors"]) == 1
    assert result["errors"][0].subgraph == "ingestion"
    assert result["errors"][0].error_type == "ValueError"
    assert result["errors"][0].recoverable is True
    assert result["edital_pages"] == []


def test_ingestion_audit_log_contains_page_count(ingestion_graph_with_mock):
    graph, _ = ingestion_graph_with_mock
    state = initial_state("edital-003", "texto", "12345678000195")

    result = graph.invoke(state)

    assert "pages=2" in result["audit_log"][0].output_summary
    assert "edital-003" in result["audit_log"][0].input_summary


def test_ingestion_audit_log_model_used(ingestion_graph_with_mock):
    graph, _ = ingestion_graph_with_mock
    state = initial_state("edital-004", "texto", "12345678000195")

    result = graph.invoke(state)

    assert result["audit_log"][0].model_used == settings.gemini_flash
