"use client";

import { useRouter } from "next/navigation";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Calendar } from "lucide-react";
import { TERMINAL_STEPS } from "@/lib/types";
import type { PipelineItem } from "@/lib/types";

function brl(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function scoreColor(score: number | null): string {
  if (score == null) return "bg-zinc-700 text-zinc-300";
  if (score >= 0.7) return "bg-green-500/15 text-green-400";
  if (score >= 0.4) return "bg-amber-500/15 text-amber-400";
  return "bg-red-500/15 text-red-400";
}

export function KanbanCard({ item }: { item: PipelineItem }) {
  const router = useRouter();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: item.run_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const deadline = item.deadline
    ? new Date(item.deadline).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })
    : null;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-zinc-800 border border-zinc-700 rounded-xl p-3 group hover:border-zinc-600 transition-colors"
    >
      <div className="flex items-start gap-2">
        <button
          {...attributes}
          {...listeners}
          aria-label="Arrastar card"
          className="text-zinc-600 hover:text-zinc-400 cursor-grab active:cursor-grabbing touch-none mt-0.5"
        >
          <GripVertical className="w-4 h-4" />
        </button>
        <div
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() =>
            router.push(
              TERMINAL_STEPS.has(item.stage) ? `/runs/${item.run_id}/result` : `/runs/${item.run_id}`
            )
          }
        >
          <p className="text-xs font-medium text-zinc-200 truncate">{item.orgao || item.edital_id.slice(0, 24)}</p>
          {item.objeto && <p className="text-[11px] text-zinc-500 truncate mt-0.5">{item.objeto}</p>}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {item.valor_estimado_brl > 0 && (
              <span className="text-[11px] font-semibold text-zinc-300">{brl(item.valor_estimado_brl)}</span>
            )}
            {item.bid_score != null && (
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${scoreColor(item.bid_score)}`}>
                score {Math.round(item.bid_score * 100)}
              </span>
            )}
            {deadline && (
              <span className="text-[10px] text-zinc-500 flex items-center gap-0.5">
                <Calendar className="w-3 h-3" /> {deadline}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
