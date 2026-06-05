"use client";

import { useQuery } from "@tanstack/react-query";
import { Kanban } from "lucide-react";
import { api } from "@/lib/api";
import { KanbanBoard } from "@/components/KanbanBoard";

export default function PipelinePage() {
  const { data: items, isLoading, isError } = useQuery({
    queryKey: ["pipeline"],
    queryFn: () => api.listPipeline(),
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <Kanban className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Pipeline</h1>
          <p className="text-xs text-zinc-500">Arraste as oportunidades entre os estágios</p>
        </div>
      </div>

      {isLoading && <p className="text-zinc-500 text-sm">Carregando pipeline…</p>}
      {isError && <p className="text-red-400 text-sm">Não foi possível carregar o pipeline.</p>}
      {items && items.length === 0 && (
        <div className="py-14 text-center bg-zinc-900 rounded-2xl border border-zinc-800">
          <Kanban className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
          <p className="text-zinc-500 text-sm">Nenhuma oportunidade no pipeline.</p>
        </div>
      )}
      {items && items.length > 0 && <KanbanBoard items={items} />}
    </div>
  );
}
