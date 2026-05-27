"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, RefreshCw, CheckCircle2, AlertTriangle, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { WatchConfig } from "@/lib/types";

export default function WatchPage() {
  const qc = useQueryClient();
  const [keywords, setKeywords] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [polling, setPolling] = useState(false);
  const [pollResult, setPollResult] = useState<"ok" | "error" | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

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
    setPollResult(null);
    setPollError(null);
    try {
      await api.triggerWatchPoll();
      await qc.invalidateQueries({ queryKey: ["watch-configs"] });
      setPollResult("ok");
    } catch (err) {
      setPollResult("error");
      setPollError(err instanceof Error ? err.message : "Erro ao consultar PNCP");
    } finally {
      setPolling(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center">
            <Eye className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-100">Watch Agent</h1>
            <p className="text-zinc-500 text-sm mt-0.5">
              Monitora o PNCP por novas licitações e alerta quando sua empresa for convocada.
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={handlePoll}
            disabled={polling}
            className="flex items-center gap-2 text-sm bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${polling ? "animate-spin" : ""}`} />
            {polling ? "Consultando…" : "Consultar agora"}
          </button>
          {pollResult === "ok" && (
            <span className="flex items-center gap-1.5 text-xs text-green-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> Consulta realizada
            </span>
          )}
          {pollResult === "error" && (
            <span className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertTriangle className="w-3.5 h-3.5" /> {pollError}
            </span>
          )}
        </div>
      </div>

      {/* Form */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
        <h2 className="font-semibold text-zinc-200 mb-4">Nova configuração</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">
              Palavras-chave <span className="text-zinc-600">(separadas por vírgula)</span>
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="ex: pregão, consultoria, TI"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">CNPJ da empresa</label>
            <input
              type="text"
              value={cnpj}
              onChange={(e) => setCnpj(e.target.value)}
              placeholder="00.000.000/0001-00"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        <button
          onClick={() => create.mutate()}
          disabled={!keywords.trim() || !cnpj.trim() || create.isPending}
          className="mt-4 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-100 px-4 py-2 rounded-lg disabled:opacity-40 transition-colors"
        >
          {create.isPending ? "Salvando…" : "Adicionar monitoramento"}
        </button>
        {create.isError && (
          <p className="text-red-400 text-xs mt-2">Erro ao salvar. Verifique os dados.</p>
        )}
      </div>

      {/* Config list */}
      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800">
          <h2 className="font-semibold text-zinc-200">Configurações ativas</h2>
        </div>
        {isLoading ? (
          <p className="text-zinc-500 text-sm py-10 text-center">Carregando…</p>
        ) : !configs?.length ? (
          <div className="py-14 text-center">
            <Eye className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-500 text-sm">Nenhum monitoramento configurado ainda.</p>
          </div>
        ) : (
          <ul className="divide-y divide-zinc-800/60">
            {configs.map((cfg: WatchConfig) => (
              <li key={cfg.id} className="px-6 py-4 flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.active ? "bg-green-500" : "bg-zinc-600"}`}
                    />
                    <span className="text-sm font-medium text-zinc-200">{cfg.cnpj}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-1.5">
                    {cfg.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="text-xs bg-blue-500/10 text-blue-400 rounded px-2 py-0.5"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                  {cfg.last_polled_at && (
                    <p className="text-xs text-zinc-600">
                      Última consulta: {new Date(cfg.last_polled_at).toLocaleString("pt-BR")}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => remove.mutate(cfg.id)}
                  disabled={remove.isPending}
                  className="text-zinc-600 hover:text-red-400 flex-shrink-0 transition-colors p-1"
                  title="Remover"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
