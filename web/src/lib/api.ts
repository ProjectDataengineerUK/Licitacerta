import type { HITLItem, RunCost, RunResult, RunStatus } from "./types";
import { tokenStore } from "./token-store";

const API_URL =
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

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
