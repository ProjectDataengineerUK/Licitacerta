"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";
import { Search } from "lucide-react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export default function SuportePage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId: rawRunId } = use(params);
  const [inputId, setInputId] = useState(rawRunId === "[runId]" ? "" : decodeURIComponent(rawRunId));
  const [activeId, setActiveId] = useState(rawRunId === "[runId]" ? "" : decodeURIComponent(rawRunId));

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["admin-debug-run", activeId],
    queryFn: () => adminApi.debugRun(activeId),
    enabled: !!activeId,
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setActiveId(inputId.trim());
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link href="/admin/tenants" className="text-zinc-500 hover:text-zinc-200 transition-colors">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-zinc-100">Debug de Run</h1>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          value={inputId}
          onChange={(e) => setInputId(e.target.value)}
          placeholder="run_id (UUID)"
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-red-600 font-mono"
        />
        <button
          type="submit"
          disabled={!inputId.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-40 text-sm font-semibold text-white transition-colors"
        >
          <Search className="w-4 h-4" />
          Inspecionar
        </button>
      </form>

      {isLoading && <p className="text-sm text-zinc-500">Carregando...</p>}
      {isError && <p className="text-sm text-red-400">Erro: {String(error)}</p>}

      {data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-xs text-zinc-500 mb-1">Run ID</p>
              <p className="text-sm font-mono text-zinc-300">{data.run_id}</p>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
              <p className="text-xs text-zinc-500 mb-1">Último step</p>
              <p className="text-sm font-mono text-zinc-300">{data.last_step}</p>
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
            <h2 className="text-sm font-semibold text-zinc-400">
              Chaves do snapshot ({data.snapshot_keys.length})
            </h2>
            <div className="flex flex-wrap gap-2">
              {data.snapshot_keys.map((k) => (
                <span key={k} className="text-xs font-mono bg-zinc-800 text-zinc-400 px-2 py-1 rounded-md">
                  {k}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-zinc-400 mb-3">Snapshot completo</h2>
            <pre className="text-xs text-zinc-400 overflow-auto max-h-96 bg-zinc-950 rounded-lg p-4">
              {JSON.stringify(data.snapshot, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
