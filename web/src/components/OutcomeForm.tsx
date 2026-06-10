"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Props {
  runId: string;
  onClose: () => void;
}

export function OutcomeForm({ runId, onClose }: Props) {
  const qc = useQueryClient();
  const [resultado, setResultado] = useState<"ganhou" | "perdeu" | "desistiu">("perdeu");
  const [precoVencedor, setPrecoVencedor] = useState("");
  const [precoPropost, setPrecoPropost] = useState("");
  const [obs, setObs] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      api.postOutcome(runId, {
        resultado,
        preco_vencedor: precoVencedor || null,
        preco_proposto: precoPropost || null,
        observacao: obs || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["historico"] });
      onClose();
    },
  });

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {(["ganhou", "perdeu", "desistiu"] as const).map((r) => (
          <button
            key={r}
            onClick={() => setResultado(r)}
            className={`flex-1 text-sm py-2 rounded-lg border transition-colors ${
              resultado === r
                ? "bg-blue-600 border-blue-500 text-white"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      <input
        value={precoVencedor}
        onChange={(e) => setPrecoVencedor(e.target.value)}
        placeholder="Preço vencedor (R$)"
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200"
      />
      <input
        value={precoPropost}
        onChange={(e) => setPrecoPropost(e.target.value)}
        placeholder="Preço proposto (R$)"
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200"
      />
      <textarea
        value={obs}
        onChange={(e) => setObs(e.target.value)}
        rows={3}
        placeholder="Observação (opcional)"
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 resize-none"
      />
      {mut.isError && (
        <p className="text-xs text-red-400">
          {mut.error instanceof Error ? mut.error.message : "Erro ao salvar"}
        </p>
      )}
      <button
        onClick={() => mut.mutate()}
        disabled={mut.isPending}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-lg disabled:opacity-50"
      >
        {mut.isPending ? "Salvando..." : "Registrar Resultado"}
      </button>
    </div>
  );
}
