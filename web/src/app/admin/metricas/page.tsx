"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";
import { Users, Activity, TrendingUp, AlertTriangle, DollarSign } from "lucide-react";

function Stat({ label, value, icon: Icon, danger }: {
  label: string; value: string | number; icon: React.ElementType; danger?: boolean;
}) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-1">
      <div className="flex items-center gap-2 text-zinc-500 text-xs mb-2">
        <Icon className="w-4 h-4" />
        {label}
      </div>
      <p className={`text-2xl font-bold ${danger ? "text-red-400" : "text-zinc-100"}`}>{value}</p>
    </div>
  );
}

export default function MetricasPage() {
  const dash = useQuery({ queryKey: ["admin-dashboard"], queryFn: adminApi.getDashboard });
  const ia = useQuery({ queryKey: ["admin-metricas-ia"], queryFn: adminApi.getMetricasIA });

  if (dash.isLoading) return <p className="text-sm text-zinc-500">Carregando...</p>;
  if (dash.isError) return <p className="text-sm text-red-400">Erro: {String(dash.error)}</p>;

  const d = dash.data!;
  const m = ia.data;

  const nivelColors = { critical: "text-red-400", warning: "text-yellow-400", info: "text-blue-400" };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-zinc-100">Métricas</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Stat label="Tenants ativos" value={d.tenants_ativos} icon={Users} />
        <Stat label="Runs hoje" value={d.runs_hoje} icon={Activity} />
        <Stat label="Runs semana" value={d.runs_semana} icon={TrendingUp} />
        <Stat label="Erros 24h" value={d.erros_24h} icon={AlertTriangle} danger={d.erros_24h > 5} />
        <Stat label="Custo LLM hoje" value={`R$ ${d.custo_llm_hoje_brl.toFixed(2)}`} icon={DollarSign} />
        {m && (
          <Stat label="Taxa HITL" value={`${(m.taxa_hitl * 100).toFixed(1)}%`} icon={Activity} />
        )}
      </div>

      {d.alertas.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-zinc-400">Alertas</h2>
          {d.alertas.map((a, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-3 flex items-center gap-3">
              <AlertTriangle className={`w-4 h-4 ${nivelColors[a.nivel]}`} />
              <span className="text-sm text-zinc-300">{a.mensagem}</span>
            </div>
          ))}
        </div>
      )}

      {m && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-zinc-400 mb-4">Distribuição de steps ({m.total_runs} runs)</h2>
          <div className="space-y-2">
            {Object.entries(m.distribuicao_steps)
              .sort((a, b) => b[1] - a[1])
              .map(([step, count]) => (
                <div key={step} className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500 w-40 truncate">{step}</span>
                  <div className="flex-1 bg-zinc-800 rounded-full h-2">
                    <div
                      className="bg-red-700 h-2 rounded-full"
                      style={{ width: `${Math.round((count / m.total_runs) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-400 w-8 text-right">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
