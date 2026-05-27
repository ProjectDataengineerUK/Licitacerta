from __future__ import annotations

EVAL_CASES = [
    {
        "id": "eval-001",
        "description": "Pregão eletrônico padrão — extração completa de campos",
        "context": {
            "edital_id": "PE-2024-001",
            "edital_pages": (
                "PREGÃO ELETRÔNICO Nº 001/2024\n"
                "ÓRGÃO: Secretaria de Educação do Estado de São Paulo\n"
                "OBJETO: Aquisição de licenças de software educacional para 500 escolas.\n"
                "VALOR ESTIMADO: R$ 3.000.000,00\n"
                "DATA DE ABERTURA: 15/06/2024 às 10:00\n"
                "CRITÉRIO DE JULGAMENTO: Menor Preço por Item\n"
                "DOCUMENTOS: CNPJ ativo, CND Federal, CND Estadual, CRF do FGTS.\n"
                "EXIGÊNCIAS TÉCNICAS: Atestado de fornecimento de software para órgão público.\n"
                "PRAZO DE ENTREGA: 30 dias após assinatura do contrato.\n"
                "PENALIDADES: Multa de 5% por atraso.\n"
            ),
        },
        "expected_modalidade": "pregao_eletronico",
        "expected_has_valor": True,
    },
    {
        "id": "eval-002",
        "description": "Concorrência de obra — extração com garantia e prazo",
        "context": {
            "edital_id": "CO-2024-003",
            "edital_pages": (
                "CONCORRÊNCIA PÚBLICA Nº 003/2024\n"
                "ÓRGÃO: Departamento Nacional de Infraestrutura de Transportes (DNIT)\n"
                "OBJETO: Construção de trecho rodoviário com 15 km de extensão, incluindo pavimentação "
                "asfáltica, drenagem e sinalização.\n"
                "VALOR ESTIMADO: R$ 45.000.000,00\n"
                "MODALIDADE: Concorrência — Lei 14.133/2021, Art. 28\n"
                "PRAZO DE EXECUÇÃO: 24 meses\n"
                "GARANTIA CONTRATUAL: 5% do valor total\n"
                "REGISTRO NO CREA: Obrigatório\n"
                "ATESTADO TÉCNICO: Execução de pavimentação asfáltica em vias com volume mínimo de "
                "500.000 m² de CBUQ.\n"
                "PRAZO PAGAMENTO: 30 dias após medição.\n"
            ),
        },
        "expected_modalidade": "concorrencia",
        "expected_has_valor": True,
    },
    {
        "id": "eval-003",
        "description": "Dispensa de licitação — extração sem modalidade padrão",
        "context": {
            "edital_id": "DL-2024-012",
            "edital_pages": (
                "AVISO DE DISPENSA DE LICITAÇÃO Nº 012/2024\n"
                "FUNDAMENTO: Art. 75, II, Lei 14.133/2021 (valor inferior ao limite)\n"
                "OBJETO: Contratação de serviço de manutenção preventiva de ar-condicionado.\n"
                "VALOR ESTIMADO: R$ 15.000,00\n"
                "PRAZO DO CONTRATO: 12 meses\n"
                "PAGAMENTO: Mensal, 30 dias após a prestação.\n"
            ),
        },
        "expected_modalidade": "dispensa",
        "expected_has_valor": True,
    },
    {
        "id": "eval-004",
        "description": "Credenciamento — formato diferenciado sem valor único",
        "context": {
            "edital_id": "CR-2024-001",
            "edital_pages": (
                "CHAMAMENTO PÚBLICO PARA CREDENCIAMENTO Nº 001/2024\n"
                "OBJETO: Credenciamento de profissionais médicos especialistas para prestação de serviços "
                "ao SUS municipal nas especialidades de cardiologia, ortopedia e neurologia.\n"
                "REMUNERAÇÃO: Tabela SUS vigente\n"
                "VIGÊNCIA: 12 meses, prorrogável\n"
                "REQUISITO: Registro no CRM, especialização comprovada.\n"
            ),
        },
        "expected_modalidade": "credenciamento",
        "expected_has_valor": False,
    },
]
