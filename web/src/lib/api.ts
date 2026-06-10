import type {
  Alert, ApprovalStatus, ApprovalStatusResult, Certidao, ContractAlert,
  ContractDashboard, DashboardSummary, DigestConfig, DigestHistoricoItem,
  HealthScore, HITLItem, NotifPrefs, PipelineItem, PipelineStage, Prediction,
  RunComment, RunCost, RunResult, RunStatus, TenantInvite, TenantMember,
  TenantProfile, UsersListOut, WatchConfig,
} from "./types";
import { tokenStore } from "./token-store";

// No browser: /api/proxy/* → Route Handler server-side (sem CORS, lê API_INTERNAL_URL em runtime)
// No servidor SSR: direto para o backend
const API_URL = typeof window === "undefined"
  ? (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : "/api/proxy";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = tokenStore.get();
  const fullUrl = `${API_URL}${path}`;
  const method = init?.method ?? "GET";

  let res: Response;
  try {
    res = await fetch(fullUrl, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...init?.headers,
      },
    });
  } catch (cause) {
    const msg = cause instanceof Error ? cause.message : String(cause);
    throw new Error(`[${method} ${fullUrl}] Sem resposta do servidor: ${msg}`);
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`[${method} ${fullUrl}] HTTP ${res.status}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  get: (path: string) => apiFetch<Record<string, any>>(path),

  analyze: (edital_raw: string, cnpj: string) =>
    apiFetch<{ run_id: string }>("/analyze", {
      method: "POST",
      body: JSON.stringify({ edital_raw, cnpj }),
    }),

  getRun: (id: string) => apiFetch<RunStatus>(`/runs/${id}`),

  listRuns: (step?: string) =>
    apiFetch<RunStatus[]>(`/runs${step ? `?step=${encodeURIComponent(step)}` : ""}`),

  getResult: (id: string) => apiFetch<RunResult>(`/runs/${id}/results`),

  getCost: (id: string) => apiFetch<RunCost>(`/runs/${id}/cost`),

  approve: (id: string, body: { approver: string; comment: string }) =>
    apiFetch<RunStatus>(`/runs/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  reject: (id: string, body: { approver: string; reason: string }) =>
    apiFetch<RunStatus>(`/runs/${id}/reject`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listHITL: () => apiFetch<{ items: HITLItem[] }>("/hitl"),

  listWatchConfigs: () => apiFetch<WatchConfig[]>("/watch/configs"),
  createWatchConfig: (body: { keywords: string[]; cnpj: string }) =>
    apiFetch<WatchConfig>("/watch/configs", { method: "POST", body: JSON.stringify(body) }),
  deleteWatchConfig: (id: string) =>
    apiFetch<void>(`/watch/configs/${id}`, { method: "DELETE" }),
  triggerWatchPoll: () =>
    apiFetch<{ status: string }>("/watch/poll", { method: "POST" }),

  listCertidoes: () => apiFetch<{ certidoes: Certidao[] }>("/certidoes"),
  uploadCertidao: (file: File, tipo: string) => {
    const form = new FormData();
    form.append("file", file);
    const token = tokenStore.get();
    return fetch(`${API_URL}/certidoes?tipo=${encodeURIComponent(tipo)}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    }).then(async (r) => {
      if (!r.ok) throw new Error(`${r.status}: ${await r.text().catch(() => r.statusText)}`);
      return r.json() as Promise<{ id: string; status: string }>;
    });
  },

  // ─── Cockpit V2 ───────────────────────────────────────────────────
  getDashboardSummary: () => apiFetch<DashboardSummary>("/dashboard/summary"),

  listPipeline: () => apiFetch<PipelineItem[]>("/pipeline"),
  updateStage: (runId: string, stage: PipelineStage) =>
    apiFetch<PipelineItem>(`/pipeline/${runId}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ stage }),
    }),

  getContractsDashboard: () => apiFetch<ContractDashboard>("/contracts/dashboard"),
  listContractAlerts: () => apiFetch<ContractAlert[]>("/contracts/alerts"),

  listAlerts: () => apiFetch<Alert[]>("/alerts"),
  markAlertsRead: (ids: string[]) =>
    apiFetch<{ marked: number }>("/alerts/mark-read", {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),

  listPredictions: () => apiFetch<Prediction[]>("/radar/predictions"),

  getHealthScore: () => apiFetch<HealthScore>("/health-score"),

  // ─── Billing ─────────────────────────────────────────────────────
  getBillingUsage: () =>
    apiFetch<{ plan: string; subscription_status: string; usado: number; limite: number | null; reset_em: string | null }>("/billing/usage"),
  listPlans: () =>
    apiFetch<{ nome: string; preco_mensal_brl: number; quota_analises_mes: number | null; feature_proposta: boolean }[]>("/billing/plans"),

  // ─── Config / Painel Usuário ──────────────────────────────────────
  getEmpresa: () => apiFetch<TenantProfile>("/config/empresa"),
  patchEmpresa: (body: Partial<TenantProfile>) =>
    apiFetch<TenantProfile>("/config/empresa", { method: "PATCH", body: JSON.stringify(body) }),

  listUsuarios: () => apiFetch<UsersListOut>("/config/usuarios"),
  convidarUsuario: (body: { email: string; papel: string }) =>
    apiFetch<TenantInvite>("/config/usuarios/convidar", { method: "POST", body: JSON.stringify(body) }),
  revogarMembro: (id: string) =>
    apiFetch<void>(`/config/usuarios/${id}`, { method: "DELETE" }),
  alterarPapel: (id: string, papel: string) =>
    apiFetch<TenantMember>(`/config/usuarios/${id}/papel`, { method: "PATCH", body: JSON.stringify({ papel }) }),
  aceitarConvite: (token: string, user_uid: string) =>
    apiFetch<TenantMember>("/config/usuarios/aceitar-convite", { method: "POST", body: JSON.stringify({ token, user_uid }) }),

  getNotifPrefs: () => apiFetch<NotifPrefs>("/config/notificacoes"),
  patchNotifPrefs: (body: Partial<NotifPrefs>) =>
    apiFetch<NotifPrefs>("/config/notificacoes", { method: "PATCH", body: JSON.stringify(body) }),

  exportDados: () => apiFetch<Record<string, unknown>>("/config/dados/export"),
  solicitarExclusao: () =>
    apiFetch<{ status: string; mensagem: string }>("/config/dados", { method: "DELETE" }),

  approveHITL: (runId: string, notes: string) =>
    apiFetch<{ decision: string }>(`/hitl/${runId}/approve`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  rejectHITL: (runId: string, notes: string) =>
    apiFetch<{ decision: string }>(`/hitl/${runId}/reject`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  // ─── LGPD ─────────────────────────────────────────────────────────
  postConsent: (body: { accepted_tou: boolean; accepted_privacy: boolean }) =>
    apiFetch<{ status: string; version: string }>("/lgpd/consent", { method: "POST", body: JSON.stringify(body) }),
  getConsentStatus: () =>
    apiFetch<{ has_consent: boolean; needs_consent: boolean; version: string }>("/lgpd/consent/status"),
  revogarLgpd: () => apiFetch<{ status: string; mensagem: string }>("/account/lgpd/revogar", { method: "DELETE" }),

  // ─── Certidões ────────────────────────────────────────────────────
  listCertidoesV2: () => apiFetch<{ certidoes: Certidao[] }>("/certidoes"),
  criarCertidao: (body: { cnpj: string; tipo: string; validade: string; url_documento?: string }) =>
    apiFetch<Certidao>("/certidoes", { method: "POST", body: JSON.stringify(body) }),
  atualizarCertidao: (id: string, body: { validade: string; url_documento?: string }) =>
    apiFetch<Certidao>(`/certidoes/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  getAlertasCertidoes: () => apiFetch<{ alertas: unknown[] }>("/certidoes/alertas"),

  // ─── Exportação de Proposta ───────────────────────────────────────
  exportProposal: (runId: string, body: { formato: "docx" | "pdf" | "html" }) =>
    apiFetch<{ version_id: string; download_url: string | null }>(`/runs/${runId}/proposal/export`, {
      method: "POST", body: JSON.stringify(body),
    }),
  listProposalVersions: (runId: string) =>
    apiFetch<unknown[]>(`/runs/${runId}/proposal/versions`),
  getProposalPreview: (runId: string) =>
    apiFetch<{ html: string }>(`/runs/${runId}/proposal/preview`),

  // ─── Ativação / Onboarding ────────────────────────────────────────
  getAtivacaoStatus: () => apiFetch<{ ativado: boolean; step: number }>("/ativacao/status"),
  cnpjLookup: (cnpj: string) => apiFetch<Record<string, unknown>>(`/ativacao/cnpj-lookup?cnpj=${encodeURIComponent(cnpj)}`),
  updateAtivacaoStep: (step: number, flags: Record<string, unknown>) =>
    apiFetch<{ step: number }>("/ativacao/step", { method: "POST", body: JSON.stringify({ step, flags }) }),
  concluirAtivacao: () => apiFetch<{ ativado: boolean }>("/ativacao/concluir", { method: "POST" }),
  submitEdital: (body: Record<string, unknown>) =>
    apiFetch<{ run_id: string }>("/analyze", { method: "POST", body: JSON.stringify(body) }),
  getRunResult: (runId: string) => apiFetch<RunResult>(`/runs/${runId}/results`),

  // ─── Outcome Learning ─────────────────────────────────────────────
  postOutcome: (runId: string, body: Record<string, unknown>) =>
    apiFetch<unknown>(`/runs/${runId}/outcome`, { method: "POST", body: JSON.stringify(body) }),
  getOutcome: (runId: string) => apiFetch<unknown>(`/runs/${runId}/outcome`),
  getHistorico: (limit = 50) => apiFetch<unknown[]>(`/historico?limit=${limit}`),
  getHistoricoStats: () => apiFetch<unknown[]>("/historico/stats"),
  exportHistorico: () => apiFetch<string>("/historico/export"),

  // ─── Digest ───────────────────────────────────────────────────────
  getDigestConfig: () => apiFetch<DigestConfig>("/digest/config"),
  putDigestConfig: (body: Partial<DigestConfig>) =>
    apiFetch<DigestConfig>("/digest/config", { method: "PUT", body: JSON.stringify(body) }),
  getDigestHistorico: (limit = 30) =>
    apiFetch<DigestHistoricoItem[]>(`/digest/historico?limit=${limit}`),

  // ─── Colaboração ──────────────────────────────────────────────────
  colaboracao: {
    listComments: (runId: string) =>
      apiFetch<RunComment[]>(`/colaboracao/${encodeURIComponent(runId)}/comentarios`),
    addComment: (runId: string, texto: string) =>
      apiFetch<RunComment>(`/colaboracao/${encodeURIComponent(runId)}/comentarios`, {
        method: "POST", body: JSON.stringify({ texto }),
      }),
    deleteComment: (runId: string, commentId: string) =>
      apiFetch<void>(`/colaboracao/${encodeURIComponent(runId)}/comentarios/${commentId}`, {
        method: "DELETE",
      }),
    getStatus: (runId: string) =>
      apiFetch<ApprovalStatusResult>(`/colaboracao/${encodeURIComponent(runId)}/status`),
    updateStatus: (runId: string, status: ApprovalStatus) =>
      apiFetch<ApprovalStatusResult>(`/colaboracao/${encodeURIComponent(runId)}/status`, {
        method: "PATCH", body: JSON.stringify({ status }),
      }),
  },
};
