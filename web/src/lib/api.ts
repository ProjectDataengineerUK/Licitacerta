import type {
  Alert, Certidao, ContractAlert, ContractDashboard, DashboardSummary,
  HealthScore, HITLItem, PipelineItem, PipelineStage, Prediction,
  RunCost, RunResult, RunStatus, WatchConfig,
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
};
