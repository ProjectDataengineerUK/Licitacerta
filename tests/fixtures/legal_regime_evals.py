from __future__ import annotations

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Lei 14.133/2021 — pregão eletrônico padrão federal",
        "context": {
            "edital_pages": (
                "PREGÃO ELETRÔNICO Nº 001/2024\n"
                "Fundamento legal: Lei nº 14.133, de 1º de abril de 2021, e Decreto Federal nº 10.024/2019.\n"
                "OBJETO: Aquisição de equipamentos de TI para uso administrativo.\n"
                "MODALIDADE: Pregão Eletrônico\n"
                "ÓRGÃO: Ministério da Gestão e da Inovação em Serviços Públicos\n"
                "VALOR ESTIMADO: R$ 500.000,00\n"
            ),
        },
        "expected_primary_law": "Lei 14.133/2021",
        "expected_modality": "pregao_eletronico",
    },
    {
        "id": "eval-002",
        "description": "Lei 13.303/2016 — empresa pública (estatais)",
        "context": {
            "edital_pages": (
                "PREGÃO ELETRÔNICO Nº 020/2024\n"
                "Fundamento legal: Lei nº 13.303, de 30 de junho de 2016 (Lei das Estatais).\n"
                "OBJETO: Contratação de serviços de consultoria empresarial.\n"
                "MODALIDADE: Pregão Eletrônico (Regulamento Interno da Empresa)\n"
                "ÓRGÃO: Empresa Brasileira de Pesquisa Agropecuária (EMBRAPA)\n"
                "VALOR ESTIMADO: R$ 800.000,00\n"
            ),
        },
        "expected_primary_law": "Lei 13.303/2016",
        "expected_modality": "pregao_eletronico",
    },
    {
        "id": "eval-003",
        "description": "Lei 8.666/1993 — contrato aditivo ainda sob regime antigo",
        "context": {
            "edital_pages": (
                "TERMO ADITIVO Nº 002/2024 AO CONTRATO Nº 015/2022\n"
                "Fundamento: Lei nº 8.666, de 21 de junho de 1993, e cláusulas contratuais vigentes.\n"
                "OBJETO DO CONTRATO ORIGINAL: Prestação de serviços de vigilância e segurança patrimonial.\n"
                "PRORROGAÇÃO: 12 meses, nos termos do Art. 57, II, da Lei 8.666/93.\n"
                "VALOR DO ADITIVO: R$ 240.000,00\n"
            ),
        },
        "expected_primary_law": "Lei 8.666/1993",
        "expected_modality": "aditivo",
    },
    {
        "id": "eval-004",
        "description": "RDC — Regime Diferenciado de Contratações (obras de infraestrutura)",
        "context": {
            "edital_pages": (
                "CONCORRÊNCIA RDC ELETRÔNICO Nº 001/2024\n"
                "Fundamento legal: Lei nº 12.462, de 4 de agosto de 2011 (RDC).\n"
                "OBJETO: Execução de obra de construção de unidade básica de saúde em área rural.\n"
                "MODALIDADE: RDC Eletrônico\n"
                "REGIME DE EXECUÇÃO: Empreitada por Preço Global\n"
                "VALOR ESTIMADO: R$ 2.000.000,00\n"
            ),
        },
        "expected_primary_law": "Lei 12.462/2011",
        "expected_modality": "rdc",
    },
]
