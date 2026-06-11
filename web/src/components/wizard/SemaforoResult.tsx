"use client";

const SEMAFORO: Record<string, { label: string; color: string }> = {
  participar: { label: "Participar", color: "text-green-400 bg-green-900/30 border-green-700" },
  participar_com_ressalvas: { label: "Participar c/ atenção", color: "text-amber-400 bg-amber-900/30 border-amber-700" },
  pedir_esclarecimento: { label: "Pedir esclarecimento", color: "text-amber-400 bg-amber-900/30 border-amber-700" },
  impugnar: { label: "Impugnar edital", color: "text-red-400 bg-red-900/30 border-red-700" },
  nao_participar: { label: "Não participar", color: "text-red-400 bg-red-900/30 border-red-700" },
};

interface Props {
  recommendation: string;
  confidence?: number;
  conclusion?: string;
}

export function SemaforoResult({ recommendation, confidence, conclusion }: Props) {
  const cfg = SEMAFORO[recommendation] ?? { label: recommendation, color: "text-zinc-400 bg-zinc-800/30 border-zinc-700" };

  return (
    <div className="space-y-3">
      <div className={`border rounded-xl px-4 py-3 flex items-center gap-3 ${cfg.color}`}>
        <div className="text-2xl" aria-hidden="true">
          {recommendation === "participar" ? "✅" :
           recommendation?.startsWith("participar") || recommendation === "pedir_esclarecimento" ? "⚠️" : "🚫"}
        </div>
        <div>
          <p className="font-semibold text-sm">{cfg.label}</p>
          {confidence !== undefined && (
            <p className="text-xs opacity-75">Confiança: {Math.round(confidence * 100)}%</p>
          )}
        </div>
      </div>
      {conclusion && (
        <p className="text-sm text-zinc-300 leading-relaxed">{conclusion}</p>
      )}
    </div>
  );
}
