"use client";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "@/lib/api";

export default function HistoricoPage() {
  const { data: runs } = useQuery({
    queryKey: ["historico"],
    queryFn: () => api.getHistorico(),
  });
  const { data: stats } = useQuery({
    queryKey: ["historico-stats"],
    queryFn: () => api.getHistoricoStats(),
  });

  return (
    <div className="space-y-6 max-w-4xl mx-auto px-4 py-6">
      <h1 className="text-xl font-bold text-zinc-100">Histórico de Performance</h1>

      {stats && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-zinc-400 mb-3">Win Rate por Segmento</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={(stats as any[]).filter((r) => r.segmento && !r.g_seg)}>
              <XAxis dataKey="segmento" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
              <YAxis hide />
              <Tooltip formatter={(v) => `${v} runs`} />
              <Bar dataKey="ganhou" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="total" fill="#3f3f46" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="space-y-2">
        {((runs as any[]) || []).map((run) => (
          <div
            key={run.run_id}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center justify-between"
          >
            <div>
              <p className="text-sm text-zinc-300 font-mono">{run.run_id.slice(0, 8)}…</p>
              <p className="text-xs text-zinc-500">
                {run.segmento || "—"} · {run.uf || "—"}
              </p>
            </div>
            <span
              className={`text-xs font-semibold px-2 py-1 rounded-full ${
                run.resultado === "ganhou"
                  ? "bg-green-900/40 text-green-400"
                  : run.resultado === "perdeu"
                    ? "bg-red-900/40 text-red-400"
                    : "bg-amber-900/40 text-amber-400"
              }`}
            >
              {run.resultado}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
