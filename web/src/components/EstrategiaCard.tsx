"use client";

import { useState } from "react";

interface AcaoDireta {
  label: string;
  rota: string;
}

interface AcaoEstrategica {
  numero: number;
  categoria: "documentacao" | "precificacao" | "juridico" | "operacional" | "inteligencia";
  titulo: string;
  descricao: string;
  prazo: string;
  impacto_vitoria_pct: number;
  acao_direta?: AcaoDireta | null;
  concluida: boolean;
}

interface EstrategiaData {
  probabilidade_sem_acoes_pct: number;
  probabilidade_com_acoes_pct: number;
  acoes: AcaoEstrategica[];
  resumo_executivo: string;
  data_insuficiente?: boolean;
}

const CATEGORIA_CONFIG: Record<string, { label: string; color: string }> = {
  documentacao:  { label: "Documentação",  color: "bg-blue-100 text-blue-700 border-blue-200" },
  precificacao:  { label: "Precificação",  color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  juridico:      { label: "Jurídico",      color: "bg-violet-100 text-violet-700 border-violet-200" },
  operacional:   { label: "Operacional",   color: "bg-amber-100 text-amber-700 border-amber-200" },
  inteligencia:  { label: "Inteligência",  color: "bg-rose-100 text-rose-700 border-rose-200" },
};

function isPrazoUrgente(prazo: string): boolean {
  const lower = prazo.toLowerCase();
  return lower.includes("hoje") || lower.includes("1 dia") || lower.includes("24h");
}

interface Props {
  runId: string;
  data: EstrategiaData;
}

export function EstrategiaCard({ runId, data }: Props) {
  const [acoes, setAcoes] = useState<AcaoEstrategica[]>(data.acoes);

  async function toggleAcao(numero: number, current: boolean) {
    const next = !current;
    try {
      await fetch(`/api/runs/${runId}/estrategia/acoes/${numero}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ concluida: next }),
      });
      setAcoes((prev) =>
        prev.map((a) => (a.numero === numero ? { ...a, concluida: next } : a))
      );
    } catch {
      // silently revert — UI stays optimistic until server confirms
    }
  }

  const concluidas = acoes.filter((a) => a.concluida).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b bg-gradient-to-r from-indigo-50 to-purple-50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎯</span>
            <h2 className="font-semibold text-gray-800 text-sm">Estratégia Competitiva</h2>
          </div>
          <span className="text-xs text-gray-400">{concluidas}/{acoes.length} concluídas</span>
        </div>

        {/* Probability bar */}
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500">Atual</span>
              <span className="font-bold text-gray-700">{data.probabilidade_sem_acoes_pct.toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gray-400 rounded-full"
                style={{ width: `${data.probabilidade_sem_acoes_pct}%` }}
              />
            </div>
          </div>
          <span className="text-gray-400 text-sm">→</span>
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500">Com ações</span>
              <span className="font-bold text-emerald-700">{data.probabilidade_com_acoes_pct.toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{ width: `${data.probabilidade_com_acoes_pct}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Executive summary */}
      {data.resumo_executivo && (
        <div className="px-5 py-3 text-xs text-gray-600 border-b bg-gray-50">
          {data.resumo_executivo}
        </div>
      )}

      {/* Actions */}
      <div className="divide-y">
        {acoes.map((acao) => {
          const cat = CATEGORIA_CONFIG[acao.categoria] ?? { label: acao.categoria, color: "bg-gray-100 text-gray-600 border-gray-200" };
          const urgente = isPrazoUrgente(acao.prazo);
          return (
            <div
              key={acao.numero}
              className={`px-5 py-4 flex gap-4 items-start transition-colors ${acao.concluida ? "opacity-50 bg-gray-50" : "hover:bg-gray-50"}`}
            >
              <button
                onClick={() => toggleAcao(acao.numero, acao.concluida)}
                className={`mt-0.5 w-5 h-5 rounded flex-shrink-0 border-2 flex items-center justify-center transition-colors ${
                  acao.concluida
                    ? "bg-emerald-500 border-emerald-500 text-white"
                    : "border-gray-300 hover:border-emerald-400"
                }`}
                title={acao.concluida ? "Marcar como pendente" : "Marcar como concluída"}
              >
                {acao.concluida && (
                  <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                  </svg>
                )}
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-gray-400">#{acao.numero}</span>
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${cat.color}`}>
                    {cat.label}
                  </span>
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${urgente ? "text-red-700 bg-red-50 border border-red-200" : "text-gray-500"}`}>
                    {acao.prazo}
                  </span>
                  <span className="text-xs text-emerald-600 font-semibold ml-auto">
                    +{acao.impacto_vitoria_pct.toFixed(0)}%
                  </span>
                </div>
                <p className={`text-sm font-semibold text-gray-800 mb-1 ${acao.concluida ? "line-through" : ""}`}>
                  {acao.titulo}
                </p>
                <p className="text-xs text-gray-500">{acao.descricao}</p>
                {acao.acao_direta && (
                  <a
                    href={acao.acao_direta.rota.replace("{run_id}", runId)}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
                  >
                    {acao.acao_direta.label} →
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
