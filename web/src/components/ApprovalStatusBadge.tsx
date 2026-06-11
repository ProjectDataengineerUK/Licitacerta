"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type ApprovalStatus = "rascunho" | "em_revisao" | "aprovado" | "submetido";

const META: Record<ApprovalStatus, { label: string; cls: string }> = {
  rascunho:   { label: "Rascunho",    cls: "bg-zinc-700/50 text-zinc-300 border-zinc-600" },
  em_revisao: { label: "Em revisão",  cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  aprovado:   { label: "Aprovado",    cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  submetido:  { label: "Submetido",   cls: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
};

const TRANSICOES: Record<ApprovalStatus, ApprovalStatus[]> = {
  rascunho:   ["em_revisao"],
  em_revisao: ["aprovado", "rascunho"],
  aprovado:   ["submetido", "em_revisao"],
  submetido:  [],
};

function canTransition(from: ApprovalStatus, to: ApprovalStatus, role: string): boolean {
  if (from === "rascunho" && to === "em_revisao") return true;
  return role === "operator" || role === "admin";
}

export function ApprovalStatusBadge({ runId, status, role, onChange }: {
  runId: string;
  status: ApprovalStatus;
  role: string;
  onChange?: (next: ApprovalStatus) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const meta = META[status];
  const destinos = TRANSICOES[status].filter((to) => canTransition(status, to, role));

  const move = async (to: ApprovalStatus) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.colaboracao.updateStatus(runId, to);
      onChange?.(res.status as ApprovalStatus);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha na transição");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => destinos.length && setOpen((v) => !v)}
        disabled={destinos.length === 0}
        className={`text-[11px] font-medium px-2 py-0.5 rounded border ${meta.cls} ${destinos.length ? "cursor-pointer" : "cursor-default"}`}>
        {meta.label}
        {destinos.length > 0 && <span className="ml-1">▾</span>}
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-40 rounded border border-zinc-700 bg-zinc-900 shadow-lg">
          {destinos.map((to) => (
            <button key={to} onClick={() => move(to)} disabled={busy}
              className="block w-full px-3 py-1.5 text-left text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-40">
              → {META[to].label}
            </button>
          ))}
        </div>
      )}
      {error && <p className="absolute left-0 top-full mt-1 w-56 text-[11px] text-red-400">{error}</p>}
    </div>
  );
}
