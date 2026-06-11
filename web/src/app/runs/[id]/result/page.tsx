"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BidBanner } from "@/components/BidBanner";
import { AgentCard } from "@/components/AgentCard";
import { SupplyChainCard } from "@/components/SupplyChainCard";
import { EstrategiaCard } from "@/components/EstrategiaCard";
import { DirecionamentoCard } from "@/components/DirecionamentoCard";
import { PregoeirCard } from "@/components/PregoeirCard";

interface Props {
  params: Promise<{ id: string }>;
}

const AGENT_META: Array<{ key: string; label: string; icon: string }> = [
  { key: "eligibility",  label: "Elegibilidade",       icon: "🏢" },
  { key: "compliance",   label: "Conformidade Jurídica", icon: "⚖️" },
  { key: "blacklist",    label: "Blacklist CEIS/CNEP",  icon: "🔍" },
  { key: "pricing",      label: "Precificação",         icon: "💰" },
];

export default function ResultPage({ params }: Props) {
  const { id } = use(params);

  const { data: result, isLoading } = useQuery({
    queryKey: ["result", id],
    queryFn: () => api.getResult(id),
  });

  const { data: cost } = useQuery({
    queryKey: ["cost", id],
    queryFn: () => api.getCost(id),
  });

  const { data: estrategia } = useQuery({
    queryKey: ["estrategia", id],
    queryFn: async () => {
      const res = await fetch(`/api/runs/${id}/estrategia`);
      if (!res.ok) return null;
      return res.json();
    },
  });

  const { data: supplyChain } = useQuery({
    queryKey: ["supply-chain", id],
    queryFn: async () => {
      const res = await fetch(`/api/runs/${id}/supply-chain`);
      if (!res.ok) return null;
      return res.json();
    },
  });

  const { data: pregoeiro } = useQuery({
    queryKey: ["pregoeiro", id],
    queryFn: async () => {
      const res = await fetch(`/api/runs/${id}/pregoeiro`);
      if (!res.ok) return null;
      const data = await res.json();
      if (data?.status) return null;
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Carregando resultado…</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 text-sm mb-2">Resultado não encontrado.</p>
        <Link href="/runs" className="text-blue-600 text-sm hover:underline">
          Voltar ao histórico
        </Link>
      </div>
    );
  }

  const totalTokensIn  = cost?.agents.reduce((s, a) => s + a.tokens_in, 0) ?? 0;
  const totalTokensOut = cost?.agents.reduce((s, a) => s + a.tokens_out, 0) ?? 0;

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/runs" className="text-xs text-gray-400 hover:text-gray-600 mb-2 inline-block">
            ← Histórico
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Resultado da Análise</h1>
          <p className="text-xs text-gray-400 font-mono mt-1">{id}</p>
        </div>
      </div>

      {/* Bid decision banner */}
      {result.bid_decision && (
        <BidBanner
          recommendation={result.bid_decision.recommendation}
          confidence={result.bid_decision.confidence}
          summary={result.bid_decision.summary}
          score={(result.bid_decision as unknown as { score?: number }).score}
        />
      )}

      {/* Agent modules */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Análise por módulo
        </h2>
        <div className="space-y-3">
          {AGENT_META.map(({ key, label, icon }) => {
            const data = result[key as keyof typeof result] as Record<string, unknown> | null;
            if (!data) return null;
            return <AgentCard key={key} title={label} icon={icon} data={data} />;
          })}
        </div>
      </div>

      {/* Direcionamento */}
      {result.compliance?.direcionamento && (
        <DirecionamentoCard
          runId={id}
          data={result.compliance.direcionamento as unknown as Parameters<typeof DirecionamentoCard>[0]["data"]}
        />
      )}

      {/* Strategy */}
      {estrategia && !estrategia.data_insuficiente && (
        <EstrategiaCard runId={id} data={estrategia} />
      )}

      {/* Supply chain */}
      {supplyChain && supplyChain.status !== "nao_aplicavel" && (
        <SupplyChainCard data={supplyChain} />
      )}

      {/* Pregoeiro profile */}
      {pregoeiro && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Pregoeiro
          </h2>
          <PregoeirCard perfil={pregoeiro} />
        </div>
      )}

      {/* Cost breakdown */}
      {cost && (
        <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 text-sm">Custo da análise</h2>
            <span className="text-base font-bold text-gray-900">
              R$ {cost.total_cost_brl.toFixed(4)}
            </span>
          </div>
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-5 py-2.5 font-medium text-gray-500">Agente</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-500">Tokens entrada</th>
                <th className="text-right px-4 py-2.5 font-medium text-gray-500">Tokens saída</th>
                <th className="text-right px-5 py-2.5 font-medium text-gray-500">Custo (R$)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {cost.agents.map((a) => (
                <tr key={a.name} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5 font-medium text-gray-700">{a.name}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{a.tokens_in.toLocaleString("pt-BR")}</td>
                  <td className="px-4 py-2.5 text-right text-gray-500">{a.tokens_out.toLocaleString("pt-BR")}</td>
                  <td className="px-5 py-2.5 text-right font-semibold text-gray-700">{a.cost_brl.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 border-t">
              <tr>
                <td className="px-5 py-2.5 font-semibold text-gray-700">Total</td>
                <td className="px-4 py-2.5 text-right text-gray-600 font-medium">{totalTokensIn.toLocaleString("pt-BR")}</td>
                <td className="px-4 py-2.5 text-right text-gray-600 font-medium">{totalTokensOut.toLocaleString("pt-BR")}</td>
                <td className="px-5 py-2.5 text-right font-bold text-gray-900">R$ {cost.total_cost_brl.toFixed(4)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Errors */}
      {result.errors?.length > 0 && (
        <div className="border border-red-200 rounded-xl p-5 bg-red-50">
          <p className="font-semibold text-red-700 mb-3 text-sm flex items-center gap-2">
            <span>⛔</span> Erros registrados
          </p>
          <div className="space-y-1.5">
            {result.errors.map((e, i) => (
              <p key={i} className="text-xs text-red-600 font-mono bg-red-100 px-3 py-1.5 rounded">
                {typeof e === "object" && e !== null && "message" in e
                  ? String((e as Record<string, unknown>).message)
                  : JSON.stringify(e)}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
