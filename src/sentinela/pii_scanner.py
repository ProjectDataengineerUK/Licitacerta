"""PII scanner for prompt text before LLM submission.

Masks CPF, email, bearer tokens, CNPJ, phone numbers.
Never raises — worst case returns original text with has_pii=False.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b"), "CNPJ"),
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "EMAIL"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"), "TOKEN"),
    (re.compile(r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[\s\-]?\d{4}\b"), "PHONE"),
]


@dataclass
class PIIScanResult:
    clean: str
    found: list[tuple[str, str]] = field(default_factory=list)  # (type, original)
    has_pii: bool = False


def scan_prompt(text: str) -> PIIScanResult:
    """Scan *text* for PII; return masked version + metadata."""
    found: list[tuple[str, str]] = []
    clean = text
    for pattern, pii_type in _PATTERNS:
        for match in pattern.findall(clean):
            found.append((pii_type, match))
            clean = clean.replace(match, f"[{pii_type}-REDACTED]", 1)
    return PIIScanResult(clean=clean, found=found, has_pii=bool(found))
