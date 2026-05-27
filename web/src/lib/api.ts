import type { Certidao, HITLItem, RunCost, RunResult, RunStatus, WatchConfig } from "./types";
import { tokenStore } from "./token-store";

// No browser: /api-proxy → Next.js rewrites server-side (sem CORS, sem build-arg)
// No servidor SSR: mesmo path, Next.js resolve internamente
const API_URL = typeof window === "undefined"
  ? (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : "/api-proxy";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = tokenStore.get();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
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
