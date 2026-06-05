"use client";

import { useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCorners,
  type DragStartEvent, type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { STAGE_LABELS, STAGE_ORDER } from "@/lib/types";
import type { PipelineItem, PipelineStage } from "@/lib/types";
import { KanbanCard } from "./KanbanCard";

const STAGE_ACCENT: Record<PipelineStage, string> = {
  analisando: "border-t-blue-500",
  decidindo: "border-t-violet-500",
  preparando: "border-t-amber-500",
  disputando: "border-t-orange-500",
  ganho: "border-t-green-500",
  perdido: "border-t-red-500",
};

function Column({ stage, items }: { stage: PipelineStage; items: PipelineItem[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage });
  return (
    <div
      ref={setNodeRef}
      className={`flex-shrink-0 w-64 bg-zinc-900/60 rounded-xl border border-zinc-800 border-t-2 ${STAGE_ACCENT[stage]} ${isOver ? "ring-2 ring-blue-500/40" : ""}`}
    >
      <div className="px-3 py-2.5 flex items-center justify-between border-b border-zinc-800">
        <span className="text-xs font-semibold text-zinc-300">{STAGE_LABELS[stage]}</span>
        <span className="text-[11px] text-zinc-500 bg-zinc-800 rounded-full px-1.5">{items.length}</span>
      </div>
      <SortableContext items={items.map((i) => i.run_id)} strategy={verticalListSortingStrategy}>
        <div className="p-2 space-y-2 min-h-[80px]">
          {items.map((item) => <KanbanCard key={item.run_id} item={item} />)}
        </div>
      </SortableContext>
    </div>
  );
}

export function KanbanBoard({ items }: { items: PipelineItem[] }) {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const mutation = useMutation({
    mutationFn: ({ runId, stage }: { runId: string; stage: PipelineStage }) =>
      api.updateStage(runId, stage),
    onMutate: async ({ runId, stage }) => {
      await queryClient.cancelQueries({ queryKey: ["pipeline"] });
      const prev = queryClient.getQueryData<PipelineItem[]>(["pipeline"]);
      queryClient.setQueryData<PipelineItem[]>(["pipeline"], (old) =>
        (old ?? []).map((i) => (i.run_id === runId ? { ...i, stage } : i))
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["pipeline"], ctx.prev);
      setError("Falha ao mover o card. Alteração revertida.");
      setTimeout(() => setError(null), 4000);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["pipeline"] }),
  });

  const byStage = (stage: PipelineStage) => items.filter((i) => i.stage === stage);
  const activeItem = items.find((i) => i.run_id === activeId) ?? null;

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over) return;
    const runId = String(active.id);
    const item = items.find((i) => i.run_id === runId);
    if (!item) return;

    // `over.id` é o id da coluna (droppable) ou de um card; resolve para stage.
    const overId = String(over.id);
    const targetStage = (STAGE_ORDER as string[]).includes(overId)
      ? (overId as PipelineStage)
      : items.find((i) => i.run_id === overId)?.stage;

    if (!targetStage || targetStage === item.stage) return;
    mutation.mutate({ runId, stage: targetStage });
  }

  return (
    <div className="space-y-3">
      {error && (
        <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded px-3 py-2">{error}</p>
      )}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-3 overflow-x-auto pb-3">
          {STAGE_ORDER.map((stage) => (
            <Column key={stage} stage={stage} items={byStage(stage)} />
          ))}
        </div>
        <DragOverlay>
          {activeItem ? <KanbanCard item={activeItem} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
