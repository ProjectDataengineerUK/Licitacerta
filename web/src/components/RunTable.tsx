"use client";

import { useRouter } from "next/navigation";
import type { RunStatus } from "@/lib/types";
import { TERMINAL_STEPS } from "@/lib/types";

const STEP_LABELS: Record<string, string> = {
  completed:            "Concluído",
  decided:              "Aguardando aprovação",
  rejected:             "Rejeitado",
  ingestion_failed:     "Falha na leitura",
  understanding_failed: "Falha no entendimento",
  execution_failed:     "Falha na execução",
  subgraph_ingestion:   "Lendo edital",
  subgraph_understanding: "Entendendo",
  subgraph_validation:  "Validando",
  subgraph_decision:    "Decidindo",
};

const STEP_STYLE: Record<string, string> = {
  completed:  "bg-green-100 text-green-700",
  decided:    "bg-orange-100 text-orange-700",
  rejected:   "bg-red-100 text-red-700",
};

function stepStyle(step: string): string {
  if (STEP_STYLE[step]) return STEP_STYLE[step];
  if (step.includes("failed")) return "bg-red-100 text-red-700";
  return "bg-blue-100 text-blue-700";
}

interface RunTableProps {
  runs: RunStatus[];
}

export function RunTable({ runs }: RunTableProps) {
  const router = useRouter();

  if (runs.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-8 text-center">
        Nenhum run encontrado.
      </p>
    );
  }

  function handleClick(run: RunStatus) {
    if (TERMINAL_STEPS.has(run.current_step)) {
      router.push(`/runs/${run.run_id}/result`);
    } else {
      router.push(`/runs/${run.run_id}`);
    }
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-600">
              Edital
            </th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">
              Status
            </th>
            <th className="text-left px-4 py-3 font-medium text-gray-600">
              Decisão
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.run_id}
              onClick={() => handleClick(run)}
              className="border-b cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <td className="px-4 py-3 font-mono text-xs text-gray-600">
                {run.edital_id.slice(0, 20)}…
              </td>
              <td className="px-4 py-3">
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${stepStyle(run.current_step)}`}
                >
                  {STEP_LABELS[run.current_step] ?? run.current_step}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {run.bid_decision?.recommendation ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
