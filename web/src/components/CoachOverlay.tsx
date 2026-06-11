"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface CoachDica {
  id: string;
  titulo: string;
  descricao: string;
  categoria: string;
  rota_sugerida?: string;
  ordem: number;
}

interface OnboardingProgress {
  pct_concluido: number;
  proxima_dica: CoachDica | null;
}

const CATEGORIA_LABELS: Record<string, string> = {
  inicio:      "Início",
  analise:     "Análise",
  decisao:     "Decisão",
  proposta:    "Proposta",
  financeiro:  "Financeiro",
};

export function CoachOverlay() {
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    fetch("/api/onboarding/progress")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setProgress(data))
      .catch(() => null);
  }, []);

  if (!progress || !progress.proxima_dica || dismissed) return null;
  if (progress.pct_concluido >= 100) return null;

  const dica = progress.proxima_dica;

  const markAndDismiss = async (dispensar: boolean) => {
    setDismissed(true);
    try {
      await fetch("/api/onboarding/marcar-vista", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dica_id: dica.id, dispensar }),
      });
    } catch {
      // silent
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 w-80 max-w-[calc(100vw-2rem)]">
      <div className="bg-white border border-gray-200 rounded-2xl shadow-2xl p-5 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              {CATEGORIA_LABELS[dica.categoria] ?? dica.categoria}
            </span>
            <p className="font-semibold text-gray-900 text-sm mt-1.5">{dica.titulo}</p>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="text-gray-300 hover:text-gray-500 transition-colors text-lg leading-none mt-0.5 shrink-0"
            aria-label="Fechar"
          >
            ×
          </button>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 leading-relaxed">{dica.descricao}</p>

        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Progresso do tour</span>
            <span>{progress.pct_concluido}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${progress.pct_concluido}%` }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          {dica.rota_sugerida ? (
            <Link
              href={dica.rota_sugerida}
              onClick={() => markAndDismiss(false)}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-xl text-center transition-colors"
            >
              Ver →
            </Link>
          ) : (
            <button
              onClick={() => markAndDismiss(false)}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 rounded-xl transition-colors"
            >
              Entendido
            </button>
          )}
          <button
            onClick={() => markAndDismiss(true)}
            className="px-3 text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-xl transition-colors"
          >
            Pular
          </button>
        </div>
      </div>
    </div>
  );
}
