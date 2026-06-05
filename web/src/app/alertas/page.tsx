"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell, AlertTriangle, AlertCircle, Info, Check, ChevronRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { buildUnifiedAlerts } from "@/lib/alerts-adapter";
import type { UnifiedAlert } from "@/lib/types";

const SEV_META: Record<UnifiedAlert["severity"], { Icon: React.ElementType; cls: string; ring: string }> = {
  critical: { Icon: AlertTriangle, cls: "text-red-400", ring: "border-red-500/30 bg-red-500/10" },
  warning: { Icon: AlertCircle, cls: "text-amber-400", ring: "border-amber-500/30 bg-amber-500/10" },
  info: { Icon: Info, cls: "text-blue-400", ring: "border-zinc-700 bg-zinc-800/50" },
};

const SOURCE_LABEL: Record<UnifiedAlert["source"], string> = {
  alert: "Sistema",
  contract: "Contrato",
  certidao: "Certidão",
  prediction: "Radar PCA",
};

export default function AlertasPage() {
  const queryClient = useQueryClient();

  const { data: alerts } = useQuery({ queryKey: ["alerts"], queryFn: () => api.listAlerts(), refetchInterval: 30_000 });
  const { data: contractAlerts } = useQuery({ queryKey: ["contracts-alerts"], queryFn: () => api.listContractAlerts(), refetchInterval: 60_000 });
  const { data: certData } = useQuery({ queryKey: ["certidoes"], queryFn: () => api.listCertidoes(), refetchInterval: 60_000 });
  const { data: predictions } = useQuery({ queryKey: ["predictions"], queryFn: () => api.listPredictions(), refetchInterval: 60_000 });

  const unified = useMemo(
    () => buildUnifiedAlerts({
      alerts,
      contractAlerts,
      certidoes: certData?.certidoes,
      predictions,
    }),
    [alerts, contractAlerts, certData, predictions]
  );

  const markRead = useMutation({
    mutationFn: (id: string) => api.markAlertsRead([id]),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <Bell className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Central de alertas</h1>
          <p className="text-xs text-zinc-500">Vencimentos, contratos, certidões e editais previstos</p>
        </div>
      </div>

      {unified.length === 0 ? (
        <div className="py-14 text-center bg-zinc-900 rounded-2xl border border-zinc-800">
          <Bell className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
          <p className="text-zinc-500 text-sm">Nenhum alerta no momento. 🎉</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {unified.map((a) => {
            const meta = SEV_META[a.severity];
            return (
              <li key={a.id} className={`rounded-xl border p-4 ${meta.ring}`}>
                <div className="flex items-start gap-3">
                  <meta.Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${meta.cls}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-zinc-100">{a.title}</p>
                      <span className="text-[10px] uppercase tracking-wide text-zinc-500 bg-zinc-800 rounded px-1.5 py-0.5">
                        {SOURCE_LABEL[a.source]}
                      </span>
                      {a.prazoDias != null && (
                        <span className="text-[11px] text-zinc-400">
                          {a.prazoDias < 0 ? `${Math.abs(a.prazoDias)}d atrás` : `em ${a.prazoDias}d`}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 mt-1">{a.message}</p>
                    {a.href && (
                      <Link href={a.href} className="text-xs text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1 mt-2">
                        {a.action ?? "Ver"} <ChevronRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                  {a.canMarkRead && (
                    <button
                      onClick={() => markRead.mutate(a.id.replace(/^alert:/, ""))}
                      disabled={markRead.isPending}
                      aria-label="Marcar como lido"
                      className="text-zinc-500 hover:text-green-400 transition-colors flex-shrink-0 disabled:opacity-40"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
