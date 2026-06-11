"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";
import { useRouter } from "next/navigation";
import type { FeatureFlag } from "@/lib/types";
import { ShieldOff, Shield, Eye, Copy, ChevronLeft, Loader2 } from "lucide-react";
import Link from "next/link";

export default function TenantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const tenantId = decodeURIComponent(id);
  const qc = useQueryClient();
  const router = useRouter();
  const [impToken, setImpToken] = useState<{ token: string; expires_at: string } | null>(null);
  const [blockReason, setBlockReason] = useState("");
  const [newFeature, setNewFeature] = useState("");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["admin-tenant", tenantId],
    queryFn: () => adminApi.getTenant(tenantId),
  });

  const bloquear = useMutation({
    mutationFn: () => adminApi.bloquearTenant(tenantId, blockReason || undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] }),
  });
  const desbloquear = useMutation({
    mutationFn: () => adminApi.desbloquearTenant(tenantId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] }),
  });

  const patchFeature = useMutation({
    mutationFn: ({ feature, enabled }: { feature: string; enabled: boolean }) =>
      adminApi.patchFeature(tenantId, feature, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] }),
  });

  const addFeature = useMutation({
    mutationFn: () => adminApi.patchFeature(tenantId, newFeature, { enabled: true }),
    onSuccess: () => {
      setNewFeature("");
      qc.invalidateQueries({ queryKey: ["admin-tenant", tenantId] });
    },
  });

  const impersonate = useMutation({
    mutationFn: () => adminApi.impersonate(tenantId),
    onSuccess: (res) => setImpToken({ token: res.token, expires_at: res.expires_at }),
  });

  if (isLoading) return <p className="text-sm text-zinc-500">Carregando...</p>;
  if (isError) return <p className="text-sm text-red-400">Erro: {String(error)}</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/admin/tenants" className="text-zinc-500 hover:text-zinc-200 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-zinc-100 font-mono">{tenantId}</h1>
        {data.blocked ? (
          <span className="text-xs text-red-400 bg-red-700/20 px-2 py-0.5 rounded-full">Bloqueado</span>
        ) : (
          <span className="text-xs text-emerald-400 bg-emerald-700/20 px-2 py-0.5 rounded-full">Ativo</span>
        )}
      </div>

      {/* Info */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p className="text-xs text-zinc-500 mb-1">Plano</p>
          <p className="font-semibold text-zinc-100">{data.plan}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p className="text-xs text-zinc-500 mb-1">Runs total</p>
          <p className="font-semibold text-zinc-100">{data.runs_total}</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <p className="text-xs text-zinc-500 mb-1">Runs mês</p>
          <p className="font-semibold text-zinc-100">{data.runs_this_month}</p>
        </div>
      </div>

      {/* Block / Unblock */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400">Acesso</h2>
        {data.blocked ? (
          <div className="space-y-2">
            {data.blocked_reason && (
              <p className="text-xs text-zinc-500">Motivo: {data.blocked_reason}</p>
            )}
            <button
              onClick={() => desbloquear.mutate()}
              disabled={desbloquear.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-sm font-semibold text-white transition-colors"
            >
              {desbloquear.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              Desbloquear
            </button>
          </div>
        ) : (
          <div className="flex gap-2 items-center">
            <input
              value={blockReason}
              onChange={(e) => setBlockReason(e.target.value)}
              placeholder="Motivo (opcional)"
              className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-red-600"
            />
            <button
              onClick={() => bloquear.mutate()}
              disabled={bloquear.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-40 text-sm font-semibold text-white transition-colors"
            >
              {bloquear.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldOff className="w-4 h-4" />}
              Bloquear
            </button>
          </div>
        )}
      </div>

      {/* Feature Flags */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400">Feature Flags</h2>
        {data.features.length === 0 && (
          <p className="text-xs text-zinc-600">Nenhuma flag configurada.</p>
        )}
        <div className="space-y-2">
          {data.features.map((f: FeatureFlag) => (
            <div key={f.feature} className="flex items-center gap-3">
              <span className="text-sm text-zinc-300 flex-1 font-mono">{f.feature}</span>
              {f.expires_at && (
                <span className="text-xs text-zinc-600">
                  até {new Date(f.expires_at).toLocaleDateString("pt-BR")}
                </span>
              )}
              <button
                onClick={() => patchFeature.mutate({ feature: f.feature, enabled: !f.enabled })}
                disabled={patchFeature.isPending}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  f.enabled
                    ? "bg-emerald-700/30 text-emerald-400 hover:bg-emerald-700/50"
                    : "bg-zinc-800 text-zinc-500 hover:bg-zinc-700"
                }`}
              >
                {f.enabled ? "Ativo" : "Inativo"}
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 pt-2 border-t border-zinc-800">
          <input
            value={newFeature}
            onChange={(e) => setNewFeature(e.target.value)}
            placeholder="nova_feature"
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
          />
          <button
            onClick={() => addFeature.mutate()}
            disabled={addFeature.isPending || !newFeature.trim()}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-sm font-semibold text-white transition-colors"
          >
            Habilitar
          </button>
        </div>
      </div>

      {/* Impersonation */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400">Visualização (read-only)</h2>
        <p className="text-xs text-zinc-600">Token efêmero de 1h. Mutations bloqueadas.</p>
        {!impToken ? (
          <button
            onClick={() => impersonate.mutate()}
            disabled={impersonate.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 text-sm font-medium text-zinc-300 transition-colors"
          >
            {impersonate.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
            Gerar token
          </button>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2 bg-zinc-800 rounded-lg px-3 py-2">
              <code className="text-xs text-zinc-300 flex-1 truncate">{impToken.token}</code>
              <button
                onClick={() => navigator.clipboard.writeText(impToken.token)}
                className="text-zinc-500 hover:text-zinc-200"
              >
                <Copy className="w-3 h-3" />
              </button>
            </div>
            <p className="text-[11px] text-zinc-600">
              Expira: {new Date(impToken.expires_at).toLocaleString("pt-BR")}
            </p>
            <p className="text-[11px] text-zinc-600">
              Use como header: <code className="text-zinc-400">X-Impersonation-Token: {"{token}"}</code>
            </p>
          </div>
        )}
      </div>

      {/* Debug link */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
        <h2 className="text-sm font-semibold text-zinc-400 mb-3">Debug de runs</h2>
        <p className="text-xs text-zinc-600">
          Acesse{" "}
          <Link href="/admin/suporte/[runId]" className="text-blue-400 hover:underline">
            /admin/suporte/{"{run_id}"}
          </Link>{" "}
          para inspecionar um run específico.
        </p>
      </div>
    </div>
  );
}
