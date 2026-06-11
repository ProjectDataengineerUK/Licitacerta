"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";
import { ShieldOff, ChevronRight } from "lucide-react";

export default function TenantsPage() {
  const [filter, setFilter] = useState<"all" | "blocked" | "active">("all");

  const blocked = filter === "blocked" ? true : filter === "active" ? false : undefined;
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["admin-tenants", filter],
    queryFn: () => adminApi.listTenants(blocked),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-zinc-100">Tenants</h1>
        <div className="flex gap-1">
          {(["all", "active", "blocked"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                filter === f ? "bg-red-700/30 text-red-400" : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
              }`}
            >
              {f === "all" ? "Todos" : f === "active" ? "Ativos" : "Bloqueados"}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-sm text-zinc-500">Carregando...</p>}
      {isError && <p className="text-sm text-red-400">Erro: {String(error)}</p>}

      {data && data.length === 0 && (
        <p className="text-sm text-zinc-600">Nenhum tenant encontrado.</p>
      )}

      {data && data.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Tenant ID</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Runs total</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Criado em</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {data.map((t) => (
                <tr key={t.tenant_id} className="hover:bg-zinc-800/40 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-zinc-300">{t.tenant_id}</td>
                  <td className="px-4 py-3 text-zinc-300">{t.runs_total}</td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString("pt-BR") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {t.blocked ? (
                      <span className="inline-flex items-center gap-1 text-xs text-red-400">
                        <ShieldOff className="w-3 h-3" /> Bloqueado
                      </span>
                    ) : (
                      <span className="text-xs text-emerald-400">Ativo</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/admin/tenants/${encodeURIComponent(t.tenant_id)}`}
                      className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
                    >
                      Ver <ChevronRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
