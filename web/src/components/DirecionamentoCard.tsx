"use client";

import { useState } from "react";
import Link from "next/link";

interface SinalDetectado {
  codigo: string;
  descricao: string;
  peso: number;
  evidencia: string;
}

interface DirecionamentoData {
  score: number;
  nivel: "baixo" | "medio" | "alto";
  sinais_detectados: SinalDetectado[];
  sinais_cartel: SinalDetectado[];
  fingerprint_beneficiario?: string | null;
  recomendacao: string;
  fundamentacao_impugnacao?: string | null;
  precedentes_tcu: string[];
  impugnacao_recomendada: boolean;
}

const NIVEL_CONFIG = {
  baixo: { label: "BAIXO",  color: "text-emerald-700 bg-emerald-50 border-emerald-300", gauge: "bg-emerald-500" },
  medio: { label: "MÉDIO",  color: "text-amber-700 bg-amber-50 border-amber-300",       gauge: "bg-amber-500" },
  alto:  { label: "ALTO",   color: "text-red-700 bg-red-50 border-red-300",             gauge: "bg-red-500" },
} as const;

interface Props {
  runId: string;
  data: DirecionamentoData;
}

export function DirecionamentoCard({ runId, data }: Props) {
  const [showFund, setShowFund] = useState(false);
  const nivel = NIVEL_CONFIG[data.nivel] ?? NIVEL_CONFIG.baixo;
  const hasIssues = data.sinais_detectados.length > 0 || data.sinais_cartel.length > 0;

  return (
    <div className={`rounded-xl border shadow-sm overflow-hidden ${data.nivel === "alto" ? "border-red-300" : "border-gray-200"}`}>
      {/* Header */}
      <div className={`px-5 py-4 border-b flex items-center justify-between ${data.nivel === "alto" ? "bg-red-50" : "bg-white"}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">🔍</span>
          <h2 className="font-semibold text-gray-800 text-sm">Detecção de Direcionamento</h2>
        </div>
        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${nivel.color}`}>
          {nivel.label}
        </span>
      </div>

      <div className="px-5 py-4 space-y-4 bg-white">
        {/* Score gauge */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-gray-500">Score de risco</span>
            <span className="font-bold text-gray-700">{data.score.toFixed(0)}/100</span>
          </div>
          <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${nivel.gauge}`}
              style={{ width: `${data.score}%` }}
            />
          </div>
        </div>

        {/* Recommendation */}
        <p className="text-sm text-gray-600">{data.recomendacao}</p>

        {/* Signals */}
        {hasIssues && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Sinais detectados
            </p>
            {[...data.sinais_detectados, ...data.sinais_cartel].map((s) => (
              <div key={s.codigo} className="flex items-start gap-3 text-sm border rounded-lg px-3 py-2">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">⚠</span>
                <div className="flex-1">
                  <p className="font-medium text-gray-700">{s.descricao}</p>
                  {s.evidencia && (
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{s.evidencia}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">+{(s.peso * 100).toFixed(0)}pts</span>
              </div>
            ))}
          </div>
        )}

        {/* Fingerprint */}
        {data.fingerprint_beneficiario && (
          <div className="text-xs bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            <span className="font-semibold text-amber-700">Possível beneficiário: </span>
            <span className="font-mono text-amber-600">{data.fingerprint_beneficiario}</span>
          </div>
        )}

        {/* Fundamentação */}
        {data.fundamentacao_impugnacao && (
          <div>
            <button
              onClick={() => setShowFund((v) => !v)}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              {showFund ? "▲ Ocultar fundamentação" : "▼ Ver fundamentação jurídica"}
            </button>
            {showFund && (
              <div className="mt-2 text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-3 border whitespace-pre-wrap">
                {data.fundamentacao_impugnacao}
                {data.precedentes_tcu.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <p className="font-semibold text-gray-500 mb-1">Precedentes TCU:</p>
                    {data.precedentes_tcu.map((p, i) => (
                      <p key={i} className="text-gray-500">• {p}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* CTA */}
        {data.impugnacao_recomendada && (
          <Link
            href={`/runs/${runId}/impugnar`}
            className="block w-full text-center py-2 px-4 bg-red-600 text-white text-sm font-semibold rounded-lg hover:bg-red-700 transition-colors"
          >
            Iniciar Impugnação
          </Link>
        )}
      </div>
    </div>
  );
}
