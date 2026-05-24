# LicitaCerta AI

> Sistema multi-agente de IA para licitações públicas brasileiras, voltado a PMEs que não conseguem participar de processos licitatórios por falta de time jurídico, financeiro e operacional. A plataforma cobre todo o ciclo — do edital à proposta — com 12 agentes especializados, supervisão humana em pontos críticos e rastreabilidade completa de decisões.

---

## Stack

- **Orquestração:** LangGraph (supervisor + subgrafos ReAct)
- **Linguagem:** Python
- **Schemas:** Pydantic (structured outputs por agente)
- **API Backend:** FastAPI (planejado)
- **Banco relacional:** PostgreSQL (planejado)
- **Fila / jobs assíncronos:** Redis + Celery/RQ (planejado)
- **Armazenamento de documentos:** S3 / MinIO (planejado)
- **RAG / Vector DB:** pgvector ou Qdrant (planejado)
- **Observabilidade:** Langfuse (planejado)
- **LLMs:** Claude API (Anthropic) / compatível com outros modelos
- **OCR:** fallback para PDFs escaneados
- **Domínio jurídico:** Lei 14.133/2021, Lei 13.303/2016, jurisprudência TCU

## Estrutura

```
Licitacerta/
└── context.md          # Contexto e spec do projeto (exportado de ChatGPT)
```

> Projeto em fase de conceito/planejamento — nenhum código ainda produzido.

## Arquivos-chave

| Arquivo | Função |
|---------|--------|
| `context.md` | Análise completa do produto, arquitetura multiagente, roadmap e dores de mercado |

## Convenções

- **Linter:** não configurado
- **Formatter:** não configurado
- **Testes:** não configurado

## Como rodar

```bash
# Projeto ainda sem código — fase de especificação
# Iniciar com: /brainstorm → /define → /design → /build
```

---

## Arquitetura planejada dos 12 agentes

| Agente | Camada | Função |
|--------|--------|--------|
| Orchestrator | Supervisão | Roteia fluxo, controla etapas, chama agentes |
| Read & Parse | Ingestão | Lê PDF, OCR, extrai tabelas, preserva referências de página |
| Tender Understanding | Entendimento | Transforma edital em objeto estruturado |
| Legal Regime | Entendimento | Detecta regime jurídico (Lei 14.133, 13.303, etc.) |
| Eligibility | Validação | Verifica se empresa pode participar |
| Compliance | Validação | Riscos jurídicos, cláusulas restritivas, jurisprudência TCU |
| Blacklist | Validação | Consulta CEIS/CNEP/CEPIM (tool determinística) |
| Pricing | Decisão | Custo, impostos, margem, prazo de pagamento, cenários |
| Bid/No-Bid | Decisão | Score final: vale participar ou não? |
| Watch Agent | Operação | Monitora chat/prazo nos portais, gera alertas com HITL |
| Proposal | Execução | Gera proposta completa após aprovação humana |
| Contract | Pós-vitória | Acompanha contrato, pagamentos, reajustes, vencimentos |

## Padrão de output por agente (Pydantic)

```python
class AgentResult(BaseModel):
    conclusion: str
    confidence: float
    blocking_issues: list[Issue]
    warnings: list[str]
    evidence: list[Evidence]   # página + trecho do edital
    human_decision_required: bool
    recommended_action: str
```

---

## Agentes recomendados (agentcode)

| Agente | Quando usar |
|--------|-------------|
| `@brainstorm-agent` | Explorar novas funcionalidades, módulos e verticais |
| `@the-planner` | Planejar implementação de agentes e fluxos LangGraph |
| `@design-agent` | Desenhar arquitetura técnica detalhada |
| `@genai-architect` | Projetar sistema multiagente, orquestração, guardrails |
| `@ai-prompt-specialist` | Otimizar prompts de cada agente especializado |
| `@python-developer` | Implementar agentes, tools, schemas Pydantic |
| `@python-reviewer` | Revisar código Python e padrões LangGraph |
| `@security-reviewer` | Auditar acesso a APIs externas (CGU, PNCP, portais) |
| `@code-reviewer` | Revisão geral de qualidade e manutenibilidade |
| `@sql-optimizer` | Queries PostgreSQL para histórico de licitações e logs |

## Comandos úteis

| Comando | Quando usar |
|---------|-------------|
| `/brainstorm` | Explorar novas dores, módulos ou verticais do LicitaCerta |
| `/define` | Capturar requisitos de um agente ou módulo específico |
| `/design` | Criar especificação técnica de um agente ou fluxo |
| `/workflow` | Estruturar pipeline LangGraph end-to-end |
| `/preflight` | Verificar qualidade antes de implementar |
| `/status` | Resumo do estado atual do projeto |

---

_Gerado por `/start` em 2026-05-21._
