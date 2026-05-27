import type { BidDecision } from "@/lib/types";

const STYLES: Record<string, string> = {
  participar:              "bg-green-50  border-green-400  text-green-800",
  nao_participar:          "bg-red-50    border-red-400    text-red-800",
  pedir_esclarecimento:    "bg-yellow-50 border-yellow-400 text-yellow-800",
  impugnar:                "bg-orange-50 border-orange-400 text-orange-800",
};

const LABELS: Record<string, string> = {
  participar:           "Participar",
  nao_participar:       "Não Participar",
  pedir_esclarecimento: "Pedir Esclarecimento",
  impugnar:             "Impugnar",
};

interface BidBannerProps {
  recommendation: BidDecision["recommendation"];
  confidence: number;
  summary: string;
}

export function BidBanner({ recommendation, confidence, summary }: BidBannerProps) {
  const style = STYLES[recommendation] ?? "bg-gray-50 border-gray-400 text-gray-800";
  return (
    <div className={`rounded-xl border-2 p-6 ${style}`}>
      <p className="text-2xl font-bold">{LABELS[recommendation] ?? recommendation}</p>
      <p className="text-sm mt-1 opacity-70">
        Confiança: {(confidence * 100).toFixed(0)}%
      </p>
      <p className="mt-3 text-base leading-relaxed">{summary}</p>
    </div>
  );
}
