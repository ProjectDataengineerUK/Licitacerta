"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { WatchConfig } from "@/lib/types";

export default function WatchPage() {
  const qc = useQueryClient();
  const [keywords, setKeywords] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [polling, setPolling] = useState(false);

  const { data: configs, isLoading } = useQuery({
    queryKey: ["watch-configs"],
    queryFn: () => api.listWatchConfigs(),
    refetchInterval: 30_000,
  });

  const create = useMutation({
    mutationFn: () =>
      api.createWatchConfig({
        keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean),
        cnpj: cnpj.trim(),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watch-configs"] });
      setKeywords("");
      setCnpj("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteWatchConfig(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watch-configs"] }),
  });

  async function handlePoll() {
    setPolling(true);
    try {
      await api.triggerWatchPoll();
      await qc.invalidateQueries({ queryKey: ["watch-configs"] });
    } finally {
      setPolling(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Watch Agent</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Monitora o PNCP por novas licitações e alerta quando sua empresa for convocada.
          </p>
        </div>
        <button
          onClick={handlePoll}
          disabled={polling}
          className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {polling ? "Consultando…" : "Consultar agora"}
        </button>
      </div>

      <div className="bg-white rounded-xl border p-6 shadow-sm mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">Nova configuração</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Palavras-chave <span className="text-gray-400">(separadas por vírgula)</span>
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="ex: pregão, consultoria, TI"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CNPJ da empresa</label>
            <input
              type="text"
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="00.000.000/0001-00"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          onClick={() => create.mutate()}
          disabled={!keywords.trim() || !cnpj.trim() || create.isPending}
          className="mt-4 text-sm bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-40 transition-colors"
        >
          {create.isPending ? "Salvando…" : "Adicionar monitoramento"}
        </button>
        {create.isError && (
          <p className="text-red-500 text-xs mt-2">Erro ao salvar. Verifique os dados.</p>
        )}
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-800">Configurações ativas</h2>
        </div>
        {isLoading ? (
          <p className="text-gray-500 text-sm py-8 text-center">Carregando…</p>
        ) : !configs?.length ? (
          <p className="text-gray-400 text-sm py-8 text-center">
            Nenhum monitoramento configurado ainda.
          </p>
        ) : (
          <ul className="divide-y">
            {configs.map((cfg: WatchConfig) => (
              <li key={cfg.id} className="px-6 py-4 flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.active ? "bg-green-500" : "bg-gray-300"}`}
                    />
                    <span className="text-sm font-medium text-gray-900">{cfg.cnpj}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-1">
                    {cfg.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="text-xs bg-blue-50 text-blue-700 rounded px-2 py-0.5"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                  {cfg.last_polled_at && (
                    <p className="text-xs text-gray-400">
                      Última consulta: {new Date(cfg.last_polled_at).toLocaleString("pt-BR")}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => remove.mutate(cfg.id)}
                  disabled={remove.isPending}
                  className="text-xs text-red-500 hover:text-red-700 flex-shrink-0 transition-colors"
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
