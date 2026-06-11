"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, Download } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  runId: string;
  hasProposta: boolean;
  plan: string;
}

const PROFISSIONAL_PLANS = ["profissional", "business", "enterprise"];

export function ProposalExportCard({ runId, hasProposta, plan }: Props) {
  const canExport = PROFISSIONAL_PLANS.includes(plan);
  const [downloading, setDownloading] = useState<string | null>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: versions } = useQuery<any[]>({
    queryKey: ["proposal-versions", runId],
    queryFn: () => api.listProposalVersions(runId) as Promise<any[]>,
    enabled: canExport && hasProposta,
  });

  async function handleExport(format: "docx" | "pdf") {
    setDownloading(format);
    try {
      const res = await api.exportProposal(runId, { formato: format });
      if (res.download_url) {
        const a = document.createElement("a");
        a.href = res.download_url;
        a.download = `proposta_${runId}.${format}`;
        a.click();
      }
    } finally {
      setDownloading(null);
    }
  }

  if (!hasProposta) return null;

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 space-y-3">
      <div className="flex items-center gap-2">
        <FileText className="w-5 h-5 text-blue-400" />
        <h3 className="font-semibold text-zinc-100">Exportar Proposta</h3>
      </div>
      {!canExport ? (
        <p className="text-xs text-zinc-500">
          Disponível nos planos Profissional, Business e Enterprise
        </p>
      ) : (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => handleExport("docx")}
            disabled={!!downloading}
            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded-lg disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            {downloading === "docx" ? "Gerando..." : "DOCX"}
          </button>
          <button
            onClick={() => handleExport("pdf")}
            disabled={!!downloading}
            className="flex items-center gap-1 bg-zinc-700 hover:bg-zinc-600 text-white text-sm px-3 py-1.5 rounded-lg disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            {downloading === "pdf" ? "Gerando..." : "PDF"}
          </button>
          {versions && versions.length > 0 && (
            <select className="text-xs bg-zinc-800 text-zinc-300 border border-zinc-700 rounded px-2 py-1">
              <option>Versões anteriores ({versions.length})</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_num} {v.formato} — {v.criado_em.slice(0, 10)}
                </option>
              ))}
            </select>
          )}
        </div>
      )}
    </div>
  );
}
