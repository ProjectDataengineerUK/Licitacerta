"""Tests for PII scanner — AT-004."""
from __future__ import annotations

import pytest

from src.sentinela.pii_scanner import scan_prompt


def test_cpf_masked():
    result = scan_prompt("CPF do responsável: 123.456.789-09 aprovado")
    assert "123.456.789-09" not in result.clean
    assert "[CPF-REDACTED]" in result.clean
    assert result.has_pii is True
    assert any(t == "CPF" for t, _ in result.found)


def test_email_masked():
    result = scan_prompt("Contato: fulano@empresa.com.br para assinatura")
    assert "fulano@empresa.com.br" not in result.clean
    assert "[EMAIL-REDACTED]" in result.clean
    assert result.has_pii is True


def test_bearer_token_masked():
    result = scan_prompt("Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.abc123==")
    assert "eyJhbGciOiJSUzI1NiJ9.abc123==" not in result.clean
    assert "[TOKEN-REDACTED]" in result.clean
    assert result.has_pii is True


def test_clean_text_no_pii():
    result = scan_prompt("Edital 001/2024 — Pregão Eletrônico para aquisição de papel A4")
    assert result.has_pii is False
    assert result.found == []
    assert result.clean == "Edital 001/2024 — Pregão Eletrônico para aquisição de papel A4"


def test_multiple_pii_types():
    text = "CPF: 111.222.333-44 Email: x@y.com Token: Bearer abc123"
    result = scan_prompt(text)
    types = {t for t, _ in result.found}
    assert "CPF" in types
    assert "EMAIL" in types
    assert "TOKEN" in types
    assert result.has_pii is True
