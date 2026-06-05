"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Wallet, TrendingUp, Clock, AlertTriangle, CalendarClock,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ContractAlert } from "@/lib/types";

function brl(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function FinanceCard({
  label, value, Icon, accent,
}: { label: string; value: string; Icon: React.ElementType; accent: string }) {
  return (
    <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-5 flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${accent}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-0.5">{label}</p>
        <p className="text-2xl font-bold text-zinc-100 leading-none">{value}</p>
      </div>
    </div>
  );
}

const ALERT_STYLE: Record<ContractAlert["severity"], string> = {
  critical: "border-red-500/30 bg-red-500/10",
  warning: "border-amber-500/30 bg-amber-500/10",
  info: "border-zinc-700 bg-zinc-800/50",
};

export default function FinanceiroPage() {
  const { data: dash, isLoading } = useQuery({
    queryKey: ["contracts-dashboard"],
    queryFn: () => api.getContractsDashboard(),
    refetchInterval: 60_000,
  });

  const { data: alerts } = useQuery({
    queryKey: ["contracts-alerts"],
    queryFn: () => api.listContractAlerts(),
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center">
          <Wallet className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Financeiro</h1>
          <p className="text-xs text-zinc-500">Receita de contratos públicos (somente leitura)</p>
        </div>
      </div>

      {isLoading && <p className="text-zinc-500 text-sm">Carregando…</p>}

      {dash && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <FinanceCard label="Contratado" value={brl(dash.total_contratado_brl)} Icon={TrendingUp} accent="bg-blue-500/15 text-blue-400" />
          <FinanceCard label="Recebido" value={brl(dash.recebido_brl)} Icon={Wallet} accent="bg-green-500/15 text-green-400" />
          <FinanceCard label="A receber" value={brl(dash.a_receber_brl)} Icon={Clock} accent="bg-amber-500/15 text-amber-400" />
          <FinanceCard label="Em atraso" value={brl(dash.em_atraso_brl)} Icon={AlertTriangle} accent={dash.em_atraso_brl > 0 ? "bg-red-500/15 text-red-400" : "bg-zinc-700 text-zinc-400"} />
        </div>
      )}

      {dash && (
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-5 flex items-center gap-3">
          <CalendarClock className="w-5 h-5 text-zinc-500" />
          <p className="text-sm text-zinc-300">
            <span className="font-bold text-zinc-100">{dash.vencendo_30d}</span> contrato{dash.vencendo_30d !== 1 ? "s" : ""} vencendo nos próximos 30 dias
          </p>
        </div>
      )}

      {/* Alertas de contrato */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-300 mb-3">Alertas de contrato</h2>
        {!alerts || alerts.length === 0 ? (
          <p className="text-zinc-600 text-sm bg-zinc-900 rounded-2xl border border-zinc-800 p-5">
            Nenhum alerta de contrato.
          </p>
        ) : (
          <ul className="space-y-2">
            {alerts.map((a, i) => (
              <li key={`${a.contract_id}-${i}`} className={`rounded-xl border p-4 ${ALERT_STYLE[a.severity]}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-100">{a.mensagem}</p>
                    <p className="text-xs text-zinc-400 mt-1">{a.acao_sugerida}</p>
                  </div>
                  {a.prazo_dias != null && (
                    <span className="text-xs font-semibold text-zinc-300 whitespace-nowrap">
                      {a.prazo_dias}d
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
