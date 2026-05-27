"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RunStatus } from "@/lib/types";

function stepLabel(step: string) {
  switch (step) {
    case "subgraph_post_award": return { label: "Em execução", cls: "bg-blue-100 text-blue-700" };
    case "completed":           return { label: "Concluído",   cls: "bg-green-100 text-green-700" };
    default:                    return { label: step,          cls: "bg-gray-100 text-gray-600" };
  }
}

export default function ContractsPage() {
  const { data: postAward, isLoading: loadingPA } = useQuery({
    queryKey: ["runs", "subgraph_post_award"],
    queryFn: () => api.listRuns("subgraph_post_award"),
    refetchInterval: 60_000,
  });

  const { data: completed, isLoading: loadingC } = useQuery({
    queryKey: ["runs", "completed"],
    queryFn: () => api.listRuns("completed"),
    refetchInterval: 60_000,
  });

  const isLoading = loadingPA || loadingC;

  const contracts: RunStatus[] = [
    ...(postAward ?? []),
    ...(completed ?? []).filter(
      (r) => r.bid_decision?.recommendation === "participar"
    ),
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Contratos</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Licitações ganhas em fase de execução ou concluídas.
        </p>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Contratos ativos</h2>
          <span className="text-xs text-gray-400">
            {contracts.length} contrato{contracts.length !== 1 ? "s" : ""}
          </span>
        </div>

        {isLoading ? (
          <p className="text-gray-500 text-sm py-8 text-center">Carregando…</p>
        ) : !contracts.length ? (
          <div className="py-12 text-center">
            <p className="text-gray-400 text-sm">Nenhum contrato ativo no momento.</p>
            <p className="text-gray-300 text-xs mt-1">
              Contratos aparecem aqui após aprovação de proposta pelo agente Execução.
            </p>
          </div>
        ) : (
          <ul className="divide-y">
            {contracts.map((run: RunStatus) => {
              const { label, cls } = stepLabel(run.current_step);
              const decision = run.bid_decision;
              return (
                <li key={run.run_id} className="px-6 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2.5 py-1 rounded-full flex-shrink-0 ${cls}`}>
                          {label}
                        </span>
                        <span className="text-sm font-medium text-gray-900 truncate">
                          Edital {run.edital_id}
                        </span>
                      </div>
                      {decision?.summary && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                          {decision.summary}
                        </p>
                      )}
                      {decision?.score !== undefined && (
                        <p className="text-xs text-gray-400 mt-1">
                          Score: {(decision.score * 100).toFixed(0)}%
                          {decision.confidence !== undefined && (
                            <span className="ml-2">
                              Confiança: {(decision.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </p>
                      )}
                    </div>
                    <Link
                      href={`/runs/${run.run_id}`}
                      className="text-xs text-blue-600 hover:text-blue-800 flex-shrink-0 transition-colors"
                    >
                      Ver detalhes →
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
