"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BidBanner } from "@/components/BidBanner";
import { AgentCard } from "@/components/AgentCard";

interface Props {
  params: Promise<{ id: string }>;
}

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

  if (isLoading) {
    return (
      <p className="text-gray-500 text-sm py-12 text-center">Carregando resultado…</p>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 text-sm">Resultado não encontrado.</p>
        <Link href="/runs" className="text-blue-600 text-sm mt-2 inline-block">
          Voltar ao histórico
        </Link>
      </div>
    );
  }

  const agents: Array<[string, string]> = [
    ["eligibility", "Elegibilidade"],
    ["compliance", "Conformidade Jurídica"],
    ["blacklist", "Blacklist"],
    ["pricing", "Precificação"],
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resultado da Análise</h1>
          <p className="text-xs text-gray-400 font-mono mt-1">{id}</p>
        </div>
        <Link href="/runs" className="text-sm text-blue-600 hover:underline">
          Histórico
        </Link>
      </div>

      {result.bid_decision && (
        <BidBanner
          recommendation={result.bid_decision.recommendation}
          confidence={result.bid_decision.confidence}
          summary={result.bid_decision.summary}
        />
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Análise por módulo
        </h2>
        {agents.map(([key, label]) => {
          const data = result[key as keyof typeof result] as Record<string, unknown> | null;
          if (!data) return null;
          return <AgentCard key={key} title={label} data={data} />;
        })}
      </div>

      {cost && (
        <div className="border rounded-lg p-4 bg-gray-50 text-sm">
          <p className="font-medium text-gray-700 mb-2">Custo da análise</p>
          <div className="flex gap-6 text-xs text-gray-500">
            <span>
              Tokens entrada:{" "}
              {cost.agents.reduce((s, a) => s + a.tokens_in, 0).toLocaleString("pt-BR")}
            </span>
            <span>
              Tokens saída:{" "}
              {cost.agents.reduce((s, a) => s + a.tokens_out, 0).toLocaleString("pt-BR")}
            </span>
            <span className="font-semibold text-gray-700">
              Total: R$ {cost.total_cost_brl.toFixed(4)}
            </span>
          </div>
        </div>
      )}

      {result.errors?.length > 0 && (
        <div className="border border-red-200 rounded-lg p-4 bg-red-50 text-sm">
          <p className="font-semibold text-red-700 mb-2">Erros registrados</p>
          {result.errors.map((e, i) => (
            <p key={i} className="text-xs text-red-600 font-mono">
              {JSON.stringify(e)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
