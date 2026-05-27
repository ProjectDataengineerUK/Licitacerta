"use client";

import { useRuns } from "@/lib/hooks/useRun";
import { RunTable } from "@/components/RunTable";

export default function RunsPage() {
  const { data: runs, isLoading } = useRuns();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Histórico</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Todos os editais analisados.
        </p>
      </div>

      {isLoading ? (
        <p className="text-gray-500 text-sm py-8 text-center">Carregando…</p>
      ) : (
        <RunTable runs={runs ?? []} />
      )}
    </div>
  );
}
