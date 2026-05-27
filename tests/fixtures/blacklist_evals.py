from __future__ import annotations

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "CNPJ limpo — nenhuma restrição esperada",
        "context": {
            "company_cnpj": "12.345.678/0001-99",
        },
        "expected_any_blocked": False,
    },
    {
        "id": "eval-002",
        "description": "CNPJ inválido — deve retornar erro controlado",
        "context": {
            "company_cnpj": "00.000.000/0000-00",
        },
        "expected_any_blocked": False,
    },
    {
        "id": "eval-003",
        "description": "CNPJ formatado sem máscara — deve normalizar e consultar",
        "context": {
            "company_cnpj": "12345678000199",
        },
        "expected_any_blocked": False,
    },
    {
        "id": "eval-004",
        "description": "CNPJ de empresa fictícia conhecida — deve responder sem timeout",
        "context": {
            "company_cnpj": "11.222.333/0001-81",
        },
        "expected_any_blocked": False,
    },
]
