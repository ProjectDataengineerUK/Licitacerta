// Espelham os modelos Pydantic do backend (src/api/models.py + src/schemas/results.py)

export type StepStatus = "pending" | "running" | "completed" | "error";

export interface BidDecision {
  recommendation: "participar" | "nao_participar" | "pedir_esclarecimento" | "impugnar";
  confidence: number;
  summary: string;
  score: number;
}

export interface RunStatus {
  run_id: string;
  current_step: string;
  edital_id: string;
  bid_decision: BidDecision | null;
  pricing: Record<string, unknown> | null;
  errors: Record<string, unknown>[];
}

export interface RunResult extends RunStatus {
  tender_schema: Record<string, unknown> | null;
  eligibility: Record<string, unknown> | null;
  compliance: Record<string, unknown> | null;
  blacklist: Record<string, unknown> | null;
  proposal_draft: Record<string, unknown> | null;
  audit_log: Record<string, unknown>[];
}

export interface AgentCost {
  name: string;
  tokens_in: number;
  tokens_out: number;
  cost_brl: number;
  latency_ms: number | null;
}

export interface RunCost {
  run_id: string;
  agents: AgentCost[];
  total_cost_brl: number;
  source: "bigquery" | "memory";
}

export interface HITLItem {
  id: string;
  run_id: string;
  action_required: string;
  payload_json: string;
  status: "pending" | "approved" | "rejected";
  expires_at: string;
  created_at: string;
}

// Mapeamento de subgrafos do supervisor (src/graph/supervisor.py)
export const SUBGRAPH_STEPS: Record<string, { label: string; order: number }> = {
  subgraph_ingestion:          { label: "Leitura do edital",       order: 1 },
  subgraph_understanding:      { label: "Entendimento",             order: 2 },
  subgraph_validation:         { label: "Validação jurídica",       order: 3 },
  subgraph_decision:           { label: "Decisão financeira",       order: 4 },
  interrupt_before_execution:  { label: "Aguardando aprovação",     order: 5 },
  subgraph_execution:          { label: "Geração de proposta",      order: 6 },
  subgraph_post_award:         { label: "Pós-vitória",              order: 7 },
};

export interface WatchConfig {
  id: string;
  keywords: string[];
  cnpj: string;
  active: boolean;
  last_polled_at: string | null;
}

export interface Certidao {
  id: string;
  tipo: string;
  status: "valid" | "expired" | "expiring_soon" | "pending_review";
  valid_until: string | null;
  gcs_path: string;
  created_at: string;
}

/* ─── Cockpit V2 ─────────────────────────────────────────────────────── */

export type PipelineStage =
  | "analisando" | "decidindo" | "preparando" | "disputando" | "ganho" | "perdido";

export interface PipelineCounts {
  analisando: number;
  decidindo: number;
  preparando: number;
  disputando: number;
  ganho_mes: number;
  perdido_mes: number;
}

export interface FinanceSummary {
  receita_contratada_brl: number;
  a_receber_30d_brl: number;
  a_receber_60d_brl: number;
}

export interface DashboardSummary {
  pipeline: PipelineCounts;
  financeiro: FinanceSummary;
  taxa_vitoria_pct: number;
  alertas_criticos: number;
  alertas_warning: number;
}

export interface PipelineItem {
  run_id: string;
  edital_id: string;
  orgao: string;
  objeto: string;
  valor_estimado_brl: number;
  stage: PipelineStage;
  bid_score: number | null;
  created_at: string | null;
  deadline: string | null;
}

export interface ContractDashboard {
  total_contratado_brl: number;
  recebido_brl: number;
  a_receber_brl: number;
  em_atraso_brl: number;
  vencendo_30d: number;
}

export interface ContractAlert {
  contract_id: string;
  tipo: string;
  severity: "critical" | "warning" | "info";
  mensagem: string;
  prazo_dias: number | null;
  acao_sugerida: string;
}

export interface Alert {
  id: string;
  tenant_id: string;
  tipo: string;
  severidade: "info" | "warning" | "critical";
  titulo: string;
  mensagem: string;
  link_relativo: string | null;
  entidade_tipo: string | null;
  entidade_id: string | null;
  lido: boolean;
  created_at: string;
}

export interface Prediction {
  id: string;
  orgao_nome: string | null;
  objeto_previsto: string | null;
  valor_estimado_brl: number | null;
  data_prevista_publicacao: string;
  confianca_pct: number;
  fonte: string;
  dias_antecedencia: number;
  status: string;
}

export interface HealthScoreComponent {
  nome: string;
  score: number;
  peso?: number;
}

export interface HealthScore {
  score: number;
  label: string;
  componentes: HealthScoreComponent[];
  recomendacoes: { titulo?: string; texto?: string }[];
  delta_semana: number | null;
  calculado_em: string;
}

/** Alerta normalizado de qualquer das 4 fontes (ver alerts-adapter.ts). */
export interface UnifiedAlert {
  id: string;
  source: "alert" | "contract" | "certidao" | "prediction";
  severity: "critical" | "warning" | "info";
  title: string;
  message: string;
  prazoDias?: number;
  href?: string;
  action?: string;
  canMarkRead: boolean;
}

export const STAGE_LABELS: Record<PipelineStage, string> = {
  analisando: "Analisando",
  decidindo: "Decidindo",
  preparando: "Preparando",
  disputando: "Disputando",
  ganho: "Ganho",
  perdido: "Perdido",
};

export const STAGE_ORDER: PipelineStage[] = [
  "analisando", "decidindo", "preparando", "disputando", "ganho", "perdido",
];

export const TERMINAL_STEPS = new Set([
  "completed",
  "rejected",
  "decided",
  "ingestion_failed",
  "understanding_failed",
  "execution_failed",
]);
