import type { BidDecision } from "@/lib/types";

const CONFIG: Record<string, { bg: string; border: string; text: string; badge: string; icon: string; label: string }> = {
  participar: {
    bg: "bg-green-50", border: "border-green-400", text: "text-green-900",
    badge: "bg-green-500 text-white", icon: "✓", label: "Participar",
  },
  nao_participar: {
    bg: "bg-red-50", border: "border-red-400", text: "text-red-900",
    badge: "bg-red-500 text-white", icon: "✗", label: "Não Participar",
  },
  pedir_esclarecimento: {
    bg: "bg-yellow-50", border: "border-yellow-400", text: "text-yellow-900",
    badge: "bg-yellow-500 text-white", icon: "?", label: "Pedir Esclarecimento",
  },
  impugnar: {
    bg: "bg-orange-50", border: "border-orange-400", text: "text-orange-900",
    badge: "bg-orange-500 text-white", icon: "!", label: "Impugnar",
  },
};

interface BidBannerProps {
  recommendation: BidDecision["recommendation"];
  confidence: number;
  summary: string;
  score?: number;
}

export function BidBanner({ recommendation, confidence, summary, score }: BidBannerProps) {
  const cfg = CONFIG[recommendation] ?? {
    bg: "bg-gray-50", border: "border-gray-400", text: "text-gray-900",
    badge: "bg-gray-500 text-white", icon: "–", label: recommendation,
  };
  const confPct = Math.round(confidence * 100);
  const scorePct = score !== undefined ? Math.round(score * 100) : null;

  return (
    <div className={`rounded-2xl border-2 p-6 ${cfg.bg} ${cfg.border}`}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <span className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold ${cfg.badge}`}>
            {cfg.icon}
          </span>
          <div>
            <p className={`text-2xl font-bold ${cfg.text}`}>{cfg.label}</p>
            <p className={`text-sm opacity-60 ${cfg.text}`}>Decisão final do agente</p>
          </div>
        </div>

        <div className="flex gap-4 text-right flex-shrink-0">
          <div>
            <p className="text-xs text-gray-500 mb-1">Confiança</p>
            <div className="flex items-center gap-2">
              <div className="w-20 h-2 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className={`h-full rounded-full ${confPct >= 80 ? "bg-green-500" : confPct >= 60 ? "bg-yellow-400" : "bg-red-400"}`}
                  style={{ width: `${confPct}%` }}
                />
              </div>
              <span className={`text-sm font-bold ${cfg.text}`}>{confPct}%</span>
            </div>
          </div>
          {scorePct !== null && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Score</p>
              <div className="flex items-center gap-2">
                <div className="w-20 h-2 rounded-full bg-gray-200 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${scorePct >= 70 ? "bg-green-500" : scorePct >= 40 ? "bg-yellow-400" : "bg-red-400"}`}
                    style={{ width: `${scorePct}%` }}
                  />
                </div>
                <span className={`text-sm font-bold ${cfg.text}`}>{scorePct}%</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className={`text-base leading-relaxed ${cfg.text} opacity-80`}>{summary}</p>
    </div>
  );
}
