"""
Smoke test de ingestão real — chama o Claude via API.

Uso:
    ANTHROPIC_API_KEY=sk-ant-... .venv/bin/python scripts/smoke_ingestion.py
    ou crie .env com ANTHROPIC_API_KEY=... e rode direto.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

EDITAL_MOCK = """
PÁGINA 1
PREGÃO ELETRÔNICO Nº 001/2026
Câmara Municipal de São Paulo

Objeto: Aquisição de papel sulfite A4 75g/m², resma com 500 folhas,
conforme especificações do Anexo I.
Valor estimado total: R$ 52.000,00 (cinquenta e dois mil reais).
Critério de julgamento: menor preço por item.
Modalidade: Pregão Eletrônico — Lei nº 14.133/2021.
Data de abertura: 30/06/2026 às 10h00.

PÁGINA 2
HABILITAÇÃO JURÍDICA E FISCAL

Documentos exigidos:
- Contrato Social ou Requerimento de Empresário
- CNPJ (Cadastro Nacional de Pessoa Jurídica)
- CND Federal (Certidão Negativa de Débitos Federais)
- Certidão de Regularidade do FGTS
- Certidão Negativa de Débitos Trabalhistas (CNDT)
- Certidão Negativa de Falência

PÁGINA 3
PENALIDADES

O descumprimento das obrigações sujeitará o contratado às seguintes sanções:
- Advertência por escrito
- Multa de 0,5% por dia de atraso sobre o valor do contrato, limitada a 10%
- Suspensão temporária de participação em licitações por até 2 anos
- Declaração de inidoneidade conforme art. 156 da Lei 14.133/2021
"""


def main():
    from src.graph.state import initial_state
    from src.graph.subgraphs.ingestion import build_ingestion_subgraph

    print("Construindo subgrafo de ingestão...")
    graph = build_ingestion_subgraph()

    state = initial_state(
        edital_id="smoke-test-001",
        edital_raw=EDITAL_MOCK,
        cnpj_empresa="12345678000195",
    )

    print("Invocando ReadParseAgent via Claude Haiku...\n")
    result = graph.invoke(state)

    if result["current_step"] == "ingestion_failed":
        print("FALHOU:")
        for e in result["errors"]:
            print(f"  [{e.agent}] {e.error_type}: {e.message}")
        sys.exit(1)

    pages = result["edital_pages"]
    print(f"current_step : {result['current_step']}")
    print(f"páginas extraídas: {len(pages)}\n")

    for p in pages:
        print(f"  Página {p.page_number}: {len(p.text)} chars | tabelas={len(p.tables)} | ocr={p.is_ocr}")
        print(f"    preview: {p.text[:80].strip()!r}")
        print()

    audit = result["audit_log"][0]
    print(f"audit: subgraph={audit.subgraph} agent={audit.agent} latency={audit.latency_ms}ms")


if __name__ == "__main__":
    main()
