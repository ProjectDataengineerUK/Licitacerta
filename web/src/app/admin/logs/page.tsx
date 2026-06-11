"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";

export default function AuditLogPage() {
  const [acao, setAcao] = useState("");
  const [adminEmail, setAdminEmail] = useState("");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["admin-audit", acao, adminEmail],
    queryFn: () =>
      adminApi.getAudit({
        acao: acao || undefined,
        admin_email: adminEmail || undefined,
        limit: 200,
      }),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-zinc-100">Audit Log</h1>

      <div className="flex gap-3">
        <input
          value={adminEmail}
          onChange={(e) => setAdminEmail(e.target.value)}
          placeholder="admin@..."
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-red-600"
        />
        <input
          value={acao}
          onChange={(e) => setAcao(e.target.value)}
          placeholder="ação (ex: bloquear_tenant)"
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-red-600 flex-1"
        />
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm text-zinc-300 transition-colors"
        >
          Filtrar
        </button>
      </div>

      {isLoading && <p className="text-sm text-zinc-500">Carregando...</p>}
      {isError && <p className="text-sm text-red-400">Erro: {String(error)}</p>}

      {data && data.length === 0 && (
        <p className="text-sm text-zinc-600">Nenhum evento registrado.</p>
      )}

      {data && data.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Quando</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Admin</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Ação</th>
                <th className="px-4 py-3 text-xs font-semibold text-zinc-500">Entidade</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {data.map((e) => (
                <tr key={e.id} className="hover:bg-zinc-800/40 transition-colors">
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    {new Date(e.created_at).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400">{e.admin_email}</td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-300">{e.acao}</td>
                  <td className="px-4 py-3 text-xs text-zinc-500">
                    {e.entidade_tipo && <span className="text-zinc-600">{e.entidade_tipo}/</span>}
                    {e.entidade_id && (
                      <span className="font-mono">{e.entidade_id}</span>
                    )}
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
