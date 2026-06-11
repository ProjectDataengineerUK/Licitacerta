"""Tests for MentorAgent — AT-001..AT-006."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.mentor import MentorAgent, _parse_mentor_response, _resumo_historico
from src.schemas.mentor import MentorMessage, MentorResponse


# AT-002: pergunta juridica → tipo_resposta="juridico" e disclaimer preenchido
@pytest.mark.asyncio
async def test_stream_juridico_has_disclaimer():
    structured = MentorResponse(
        resposta="O Art. 40 proíbe...",
        tipo_resposta="juridico",
        confianca=0.9,
        disclaimer=None,
    )
    chunks = [
        MagicMock(content="O Art. 40"),
        MagicMock(content=" proíbe..."),
    ]

    async def fake_astream(_):
        for c in chunks:
            yield c

    with patch("src.agents.mentor.get_llm", return_value=MagicMock()):
        agent = MentorAgent()
    with patch.object(agent._llm, "astream", side_effect=fake_astream):
        with patch("src.agents.mentor._parse_mentor_response", return_value=structured):
            collected = []
            async for chunk in agent.stream("Esta cláusula é ilegal?", [], {}, {}):
                collected.append(chunk)

    structured_evt = next((c for c in collected if c.startswith("[STRUCTURED]")), None)
    assert structured_evt is not None
    data = MentorResponse.model_validate_json(structured_evt[len("[STRUCTURED]"):])
    assert data.tipo_resposta == "juridico"
    assert data.disclaimer is not None
    assert "jurídica especializada" in data.disclaimer


# AT-004: parse_mentor_response com JSON embebido em texto
def test_parse_structured_json_embedded():
    raw = (
        'Aqui está a resposta: {"resposta": "Sim", "tipo_resposta": "geral",'
        ' "acoes_sugeridas": [], "evidencias": [], "confianca": 0.8}'
    )
    result = _parse_mentor_response(raw)
    assert result.resposta == "Sim"
    assert result.tipo_resposta == "geral"
    assert result.confianca == 0.8


# AT-004b: parse_mentor_response com JSON inválido → fallback texto
def test_parse_fallback_on_invalid_json():
    raw = "Resposta direta sem JSON nenhum."
    result = _parse_mentor_response(raw)
    assert result.resposta == raw.strip()
    assert result.tipo_resposta == "geral"
    assert result.confianca == 0.5


# AT-005: historico_resumo inclui últimas mensagens
def test_resumo_historico_format():
    historico = [
        MentorMessage(role="user", content="Qual o prazo?"),
        MentorMessage(role="assistant", content="O prazo é de 30 dias."),
    ]
    resumo = _resumo_historico(historico)
    assert "Usuário" in resumo
    assert "Mentor" in resumo
    assert "30 dias" in resumo


def test_resumo_historico_empty():
    assert _resumo_historico([]) == "(sem histórico)"


# AT-006: acoes_sugeridas limitadas a 3
def test_parse_acoes_limit():
    data = {
        "resposta": "Texto",
        "tipo_resposta": "estrategico",
        "acoes_sugeridas": [
            {"label": "A", "rota": "/runs"},
            {"label": "B"},
            {"label": "C"},
        ],
        "evidencias": [],
        "confianca": 0.7,
    }
    result = MentorResponse(**data)
    assert len(result.acoes_sugeridas) == 3
