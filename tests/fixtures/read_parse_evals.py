from __future__ import annotations

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Edital simples de pregão eletrônico — texto bem formatado",
        "context": {
            "edital_raw": (
                "PREGÃO ELETRÔNICO Nº 001/2024\n"
                "ÓRGÃO: Prefeitura Municipal de São Paulo\n"
                "OBJETO: Aquisição de material de escritório (papel A4, canetas, grampeadores).\n"
                "VALOR ESTIMADO: R$ 25.000,00\n"
                "DATA DE ABERTURA: 10/06/2024 às 09:00\n"
                "CRITÉRIO DE JULGAMENTO: Menor Preço\n"
                "DOCUMENTOS EXIGIDOS: CNPJ ativo, CND Federal, CND Estadual, FGTS.\n"
                "PENALIDADES: Multa de 2% por dia de atraso, limitada a 10%.\n"
            ),
        },
        "expected_pages_min": 1,
        "expected_has_objeto": True,
    },
    {
        "id": "eval-002",
        "description": "Edital de obra pública com tabelas de preços",
        "context": {
            "edital_raw": (
                "CONCORRÊNCIA Nº 003/2024\n"
                "OBJETO: Execução de obra de reforma e ampliação do CRAS Municipal.\n"
                "VALOR ESTIMADO: R$ 1.500.000,00\n"
                "MODALIDADE: Concorrência (Lei 14.133/2021)\n"
                "CRITÉRIO DE JULGAMENTO: Menor Preço Global\n"
                "PRAZO DE EXECUÇÃO: 12 meses\n"
                "GARANTIA CONTRATUAL: 5% do valor do contrato\n"
                "HABILITAÇÃO TÉCNICA:\n"
                "  - Registro no CREA\n"
                "  - Responsável técnico com experiência em obras de reforma predial\n"
                "  - Atestado de execução de obras similares (mínimo R$ 750.000,00)\n"
                "PENALIDADES:\n"
                "  - Multa de 10% por rescisão culposa\n"
                "  - Multa de 0,3% por dia de atraso\n"
            ),
        },
        "expected_pages_min": 1,
        "expected_has_objeto": True,
    },
    {
        "id": "eval-003",
        "description": "Edital com cláusulas ilegais — deve extrair texto sem perda",
        "context": {
            "edital_raw": (
                "PREGÃO ELETRÔNICO Nº 010/2024\n"
                "OBJETO: Fornecimento de notebooks Dell Latitude 5540 (obrigatório) para uso administrativo.\n"
                "VALOR ESTIMADO: R$ 200.000,00\n"
                "EXIGÊNCIAS TÉCNICAS:\n"
                "  - Processador Intel Core i7 13ª geração (obrigatório)\n"
                "  - Memória RAM marca Kingston 16GB\n"
                "  - Certificado ISO 9001 do fabricante\n"
                "DOCUMENTOS EXIGIDOS:\n"
                "  - CNPJ ativo\n"
                "  - Certidão emitida por câmara de comércio internacional (sem base legal)\n"
                "  - Declaração de inexistência de processos trabalhistas nos últimos 10 anos\n"
            ),
        },
        "expected_pages_min": 1,
        "expected_has_objeto": True,
    },
]
