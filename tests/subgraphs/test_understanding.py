from unittest.mock import MagicMock, patch

import pytest

from src.config import settings
from src.graph.state import initial_state
from src.schemas.results import LegalRegimeResult
from src.schemas.tender import Evidence, PageContent, TenderSchema


def _make_pages() -> list[PageContent]:
    return [
        PageContent(page_number=1, text="Objeto: Aquisição de computadores.", tables=[], is_ocr=False),
        PageContent(
            page_number=2, text="Regime: Lei 14.133/2021. Modalidade: Pregão Eletrônico.", tables=[], is_ocr=False
        ),
    ]


def _make_tender_schema() -> TenderSchema:
    return TenderSchema(
        objeto="Aquisição de computadores",
        orgao="Prefeitura Municipal de Teste",
        modalidade="pregao_eletronico",
        criterio_julgamento="menor_preco",
        documentos_exigidos=["CNPJ", "CND Federal", "FGTS"],
        exigencias_tecnicas=["Atestado de capacidade técnica"],
        penalidades=["Multa de 10% por descumprimento"],
        evidence=[Evidence(document="edital.pdf", page=1, excerpt="Aquisição de computadores")],
    )


def _make_legal_regime() -> LegalRegimeResult:
    return LegalRegimeResult(
        primary_law="lei_14133",
        modality="pregao_eletronico",
        special_regime=None,
        confidence=0.95,
    )


@pytest.fixture()
def understanding_graph_with_mocks():
    mock_tu = MagicMock()
    mock_tu.run.return_value = _make_tender_schema()
    mock_lr = MagicMock()
    mock_lr.run.return_value = _make_legal_regime()

    with (
        patch("src.graph.subgraphs.understanding.TenderUnderstandingAgent", return_value=mock_tu),
        patch("src.graph.subgraphs.understanding.LegalRegimeAgent", return_value=mock_lr),
    ):
        from src.graph.subgraphs.understanding import build_understanding_subgraph
        graph = build_understanding_subgraph()
    return graph, mock_tu, mock_lr


def test_understanding_happy_path(understanding_graph_with_mocks):
    graph, mock_tu, mock_lr = understanding_graph_with_mocks
    state = initial_state("edital-001", "texto bruto", "12345678000195")
    state["edital_pages"] = _make_pages()

    result = graph.invoke(state)

    assert result["current_step"] == "understood"
    assert result["tender_schema"].objeto == "Aquisição de computadores"
    assert result["legal_regime"].primary_law == "lei_14133"
    assert result["legal_regime"].confidence == 0.95
    assert len(result["audit_log"]) == 2
    assert result["audit_log"][0].agent == "tender_understanding"
    assert result["audit_log"][1].agent == "legal_regime"
    assert result["errors"] == []


def test_understanding_captures_tu_error(understanding_graph_with_mocks):
    graph, mock_tu, mock_lr = understanding_graph_with_mocks
    mock_tu.run.side_effect = ValueError("contexto insuficiente")

    state = initial_state("edital-002", "texto ruim", "12345678000195")
    state["edital_pages"] = _make_pages()

    result = graph.invoke(state)

    assert result["current_step"] == "understanding_failed"
    assert len(result["errors"]) >= 1
    assert result["errors"][0].agent == "tender_understanding"


def test_understanding_audit_log_has_modelo(understanding_graph_with_mocks):
    graph, _, _ = understanding_graph_with_mocks
    state = initial_state("edital-003", "texto", "12345678000195")
    state["edital_pages"] = _make_pages()

    result = graph.invoke(state)

    tu_event = next(e for e in result["audit_log"] if e.agent == "tender_understanding")
    lr_event = next(e for e in result["audit_log"] if e.agent == "legal_regime")
    assert tu_event.model_used == settings.gemini_pro
    assert lr_event.model_used == settings.gemini_flash
