import type { AdminDashboard, AdminMetricasIA, AdminTenant, AdminTenantDetail, AuditEntry, FeatureFlag } from "./types";

const API_URL = typeof window === "undefined"
  ? (process.env.API_INTERNAL_URL || "http://localhost:8000")
  : "/api/proxy";

function getAdminKey(): string {
  if (typeof sessionStorage !== "undefined") {
    const key = sessionStorage.getItem("admin_key");
    if (key) return key;
  }
  if (typeof document !== "undefined") {
    const m = document.cookie.match(/(?:^|;\s*)admin_key=([^;]*)/);
    if (m) return decodeURIComponent(m[1]);
  }
  return "";
}

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const key = getAdminKey();
  const url = `${API_URL}${path}`;
  const method = init?.method ?? "GET";
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": key,
        ...init?.headers,
      },
    });
  } catch (cause) {
    throw new Error(`[${method} ${url}] Sem resposta do servidor`);
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`[${method} ${url}] HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const adminApi = {
  login: async (admin_key: string): Promise<void> => {
    const url = `${API_URL}/admin/login`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ admin_key }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
  },

  getDashboard: () => adminFetch<AdminDashboard>("/admin/dashboard"),

  getMetricasIA: () => adminFetch<AdminMetricasIA>("/admin/metricas/ia"),

  listTenants: (blocked?: boolean) => {
    const q = blocked !== undefined ? `?blocked=${blocked}` : "";
    return adminFetch<AdminTenant[]>(`/admin/tenants${q}`);
  },

  getTenant: (id: string) => adminFetch<AdminTenantDetail>(`/admin/tenants/${id}`),

  bloquearTenant: (id: string, reason?: string) =>
    adminFetch<{ tenant_id: string; blocked: boolean }>(`/admin/tenants/${id}/bloquear`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null }),
    }),

  desbloquearTenant: (id: string) =>
    adminFetch<{ tenant_id: string; blocked: boolean }>(`/admin/tenants/${id}/desbloquear`, {
      method: "POST",
    }),

  patchFeature: (
    tenantId: string,
    feature: string,
    body: { enabled: boolean; override?: boolean; expires_at?: string | null; note?: string | null },
  ) =>
    adminFetch<FeatureFlag>(`/admin/tenants/${tenantId}/features/${feature}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  impersonate: (tenantId: string) =>
    adminFetch<{ token: string; tenant_id: string; expires_at: string }>(
      `/admin/tenants/${tenantId}/impersonate`,
      { method: "POST" },
    ),

  getAudit: (params?: { admin_email?: string; acao?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.admin_email) q.set("admin_email", params.admin_email);
    if (params?.acao) q.set("acao", params.acao);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return adminFetch<AuditEntry[]>(`/admin/audit${qs}`);
  },

  debugRun: (runId: string) =>
    adminFetch<{ run_id: string; last_step: string; snapshot_keys: string[]; snapshot: Record<string, unknown> }>(
      `/admin/runs/${runId}/debug`,
    ),
};
