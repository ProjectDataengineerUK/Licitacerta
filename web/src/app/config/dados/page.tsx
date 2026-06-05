"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Database, Download, Trash2, Loader2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

export default function DadosPage() {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const exportar = useMutation({
    mutationFn: api.exportDados,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `licitacerta-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const excluir = useMutation({
    mutationFn: api.solicitarExclusao,
    onSuccess: () => setConfirmDelete(false),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <Database className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Dados</h1>
          <p className="text-xs text-zinc-500">Portabilidade e exclusão (LGPD)</p>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div>
          <p className="text-sm font-semibold text-zinc-100 mb-1">Exportar meus dados</p>
          <p className="text-xs text-zinc-500 mb-3">
            Baixa um arquivo JSON com todos os runs, contratos e alertas do seu tenant.
          </p>
          <button
            onClick={() => exportar.mutate()}
            disabled={exportar.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-sm font-medium text-zinc-200 transition-colors disabled:opacity-40"
          >
            {exportar.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Exportar JSON
          </button>
          {exportar.isError && (
            <p className="text-xs text-red-400 mt-2">
              {exportar.error instanceof Error ? exportar.error.message : "Erro ao exportar"}
            </p>
          )}
        </div>

        <div className="border-t border-zinc-800 pt-4">
          <p className="text-sm font-semibold text-red-400 mb-1">Solicitar exclusão de dados</p>
          <p className="text-xs text-zinc-500 mb-3">
            Solicita a exclusão de todos os dados do tenant (Art. 18, LGPD). Processado em até 30 dias.
          </p>

          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Solicitar exclusão
            </button>
          ) : (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 text-red-400">
                <AlertTriangle className="w-4 h-4" />
                <p className="text-sm font-semibold">Confirmar exclusão?</p>
              </div>
              <p className="text-xs text-zinc-400">Esta ação é irreversível. Todos os dados serão apagados.</p>
              <div className="flex gap-2">
                <button
                  onClick={() => excluir.mutate()}
                  disabled={excluir.isPending}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-sm font-semibold text-white disabled:opacity-40 transition-colors"
                >
                  {excluir.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Confirmar
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm text-zinc-300 transition-colors"
                >
                  Cancelar
                </button>
              </div>
              {excluir.isSuccess && (
                <p className="text-xs text-emerald-400">{excluir.data?.mensagem}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
