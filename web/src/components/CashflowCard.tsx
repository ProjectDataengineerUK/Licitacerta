"use client";

import Link from "next/link";

interface CashflowSimulation {
  risco: "baixo" | "medio" | "critico";
  capital_giro_necessario_brl: number;
  fluxo_mensal_brl?: number;
  meses_exposicao?: number;
  pico_negativo_brl?: number;
  recomendacao?: string;
}

const RISCO_CONFIG = {
  baixo:   { label: "Baixo",   color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  medio:   { label: "Médio",   color: "text-amber-700 bg-amber-50 border-amber-200" },
  critico: { label: "Crítico", color: "text-red-700 bg-red-50 border-red-200" },
};

const BRL = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function CashflowCard({ data, runId }: { data: CashflowSimulation; runId: string }) {
  const cfg = RISCO_CONFIG[data.risco] ?? RISCO_CONFIG.medio;

  return (
    <div className={`border rounded-xl p-5 space-y-4 ${cfg.color}`}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-base">Fluxo de Caixa</h3>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${cfg.color}`}>
          Risco {cfg.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="bg-white/60 rounded-lg p-3">
          <p className="text-xs text-gray-500">Capital de giro necessário</p>
          <p className="font-bold text-sm mt-0.5">{BRL(data.capital_giro_necessario_brl)}</p>
        </div>
        {data.pico_negativo_brl != null && (
          <div className="bg-white/60 rounded-lg p-3">
            <p className="text-xs text-gray-500">Pico negativo</p>
            <p className="font-bold text-sm mt-0.5 text-red-700">{BRL(data.pico_negativo_brl)}</p>
          </div>
        )}
        {data.meses_exposicao != null && (
          <div className="bg-white/60 rounded-lg p-3">
            <p className="text-xs text-gray-500">Exposição</p>
            <p className="font-bold text-sm mt-0.5">{data.meses_exposicao} meses</p>
          </div>
        )}
      </div>

      {data.recomendacao && (
        <p className="text-sm">{data.recomendacao}</p>
      )}

      {data.risco === "critico" && (
        <Link
          href={`/recebiveis?run_id=${runId}&valor_bruto=${Math.round(data.capital_giro_necessario_brl)}`}
          className="inline-block bg-white border border-current text-sm font-semibold px-4 py-2 rounded-lg hover:bg-red-50 transition-colors"
        >
          Simular antecipação de recebíveis →
        </Link>
      )}
    </div>
  );
}
