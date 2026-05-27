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

export const TERMINAL_STEPS = new Set([
  "completed",
  "rejected",
  "decided",
  "ingestion_failed",
  "understanding_failed",
  "execution_failed",
]);
