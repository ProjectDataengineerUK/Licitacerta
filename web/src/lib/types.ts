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

/* ─── Painel Usuário ─────────────────────────────────────────────────────── */

export type UserRole = "admin" | "analista" | "visualizador";

export interface TenantMember {
  id: string;
  user_uid: string;
  email: string;
  nome: string | null;
  papel: UserRole;
  ativo: boolean;
  created_at: string;
}

export interface TenantInvite {
  id: string;
  email: string;
  papel: UserRole;
  expires_at: string;
  accepted_at: string | null;
}

export interface TenantProfile {
  id: string;
  name: string;
  cnpj: string;
  vertical: string | null;
  segmentos: string[];
  ufs_interesse: string[];
  regime_tributario: "simples" | "lucro_presumido" | "lucro_real";
}

export interface NotifPrefs {
  email_enabled: boolean;
  whatsapp_enabled: boolean;
  whatsapp_number: string | null;
  tipos_habilitados: string[];
}

export interface UsersListOut {
  members: TenantMember[];
  invites: TenantInvite[];
}

export const TERMINAL_STEPS = new Set([
  "completed",
  "rejected",
  "decided",
  "ingestion_failed",
  "understanding_failed",
  "execution_failed",
]);

/* ─── Painel Admin ───────────────────────────────────────────────────────── */

export interface AdminDashboard {
  tenants_ativos: number;
  runs_hoje: number;
  runs_semana: number;
  custo_llm_hoje_brl: number;
  erros_24h: number;
  alertas: { nivel: "critical" | "warning" | "info"; mensagem: string }[];
}

export interface AdminMetricasIA {
  total_runs: number;
  taxa_hitl: number;
  distribuicao_steps: Record<string, number>;
}

export interface AdminTenant {
  tenant_id: string;
  blocked: boolean;
  runs_total: number;
  created_at: string;
}

export interface AdminTenantDetail {
  tenant_id: string;
  blocked: boolean;
  blocked_reason: string | null;
  runs_total: number;
  runs_this_month: number;
  plan: string;
  features: FeatureFlag[];
}

export interface FeatureFlag {
  feature: string;
  enabled: boolean;
  override: boolean;
  expires_at: string | null;
  note: string | null;
}

export interface AuditEntry {
  id: string;
  admin_email: string;
  acao: string;
  entidade_tipo: string | null;
  entidade_id: string | null;
  dados_antes: Record<string, unknown> | null;
  dados_depois: Record<string, unknown> | null;
  created_at: string;
}

/* ─── Sprint A+B ─────────────────────────────────────────────────────────── */

export interface DigestConfig {
  tenant_id: string;
  ufs: string[];
  cnaes: string[];
  valor_min: number | null;
  valor_max: number | null;
  palavras_chave: string[];
  ativo: boolean;
  canal_email: boolean;
  canal_push: boolean;
}

export interface DigestHistoricoItem {
  id: string;
  digest_date: string;
  itens_enviados: number;
  abriu_email: boolean;
  clicks: number;
  enviado_em: string;
}

export interface RunComment {
  id: string;
  run_id: string;
  user_uid: string;
  texto: string;
  mencoes: string[];
  deleted: boolean;
  created_at: string;
}

export type ApprovalStatus = "rascunho" | "em_revisao" | "aprovado" | "submetido";

export interface ApprovalStatusResult {
  run_id: string;
  status: ApprovalStatus;
  atualizado_por: string | null;
  atualizado_em: string | null;
}

export interface StatusTransition {
  from: ApprovalStatus;
  to: ApprovalStatus;
}

export interface FinanceiroTrendMonth {
  mes: string; // "YYYY-MM"
  contratado_brl: number;
  recebido_brl: number;
  a_receber_brl: number;
}

export interface FinanceiroTrend {
  months: FinanceiroTrendMonth[];
}
