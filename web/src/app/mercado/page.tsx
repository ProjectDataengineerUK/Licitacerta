"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3, TrendingUp, Building2, Users, AlertTriangle, ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";

function brl(v: number | null | undefined): string {
  if (v == null) return "—";
  return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const color =
    score >= 70 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-red-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`text-4xl font-bold ${color}`}>{score}</span>
      <span className="text-xs text-zinc-400">/100</span>
      <span
        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
          score >= 70
            ? "bg-emerald-900/40 text-emerald-300"
            : score >= 40
            ? "bg-amber-900/40 text-amber-300"
            : "bg-red-900/40 text-red-300"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function InsuficienteCard({ label }: { label: string }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex items-center gap-3 text-zinc-500">
      <AlertTriangle className="w-5 h-5 flex-shrink-0" />
      <span className="text-sm">{label} — dados insuficientes</span>
    </div>
  );
}

export default function MercadoPage() {
  const [cnpj, setCnpj] = useState("");
  const [cnpjInput, setCnpjInput] = useState("");
  const [item, setItem] = useState("");
  const [itemInput, setItemInput] = useState("");
  const [uasg, setUasg] = useState("");
  const [uasgInput, setUasgInput] = useState("");
  const [segmento, setSegmento] = useState("");
  const [segInput, setSegInput] = useState("");

  const competitor = useQuery({
    queryKey: ["competitor", cnpj],
    queryFn: () => api.get(`/market/competitor/${cnpj}`),
    enabled: !!cnpj,
  });

  const benchmark = useQuery({
    queryKey: ["benchmark", item],
    queryFn: () => api.get(`/market/prices?item=${encodeURIComponent(item)}`),
    enabled: !!item,
  });

  const organ = useQuery({
    queryKey: ["organ", uasg],
    queryFn: () => api.get(`/market/organ/${uasg}/score`),
    enabled: !!uasg,
  });

  const summary = useQuery({
    queryKey: ["summary", segmento],
    queryFn: () => api.get(`/market/summary?segmento=${encodeURIComponent(segmento)}`),
    enabled: !!segmento,
  });

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100">Inteligência de Mercado</h1>
        <p className="text-zinc-500 text-sm mt-1">
          Raio-X de concorrentes, benchmark de preços e score de órgãos pagadores
        </p>
      </div>

      {/* ── Raio-X Concorrente ── */}
      <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 text-zinc-300 font-semibold">
          <Users className="w-5 h-5 text-violet-400" />
          Raio-X de Concorrente
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            placeholder="CNPJ (somente números)"
            value={cnpjInput}
            onChange={(e) => setCnpjInput(e.target.value)}
          />
          <button
            className="bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold px-4 rounded-lg transition"
            onClick={() => setCnpj(cnpjInput.replace(/\D/g, ""))}
          >
            Buscar
          </button>
        </div>

        {competitor.isLoading && <p className="text-zinc-500 text-sm">Carregando…</p>}
        {competitor.data && competitor.data.data_insuficiente && (
          <InsuficienteCard label="Concorrente" />
        )}
        {competitor.data && !competitor.data.data_insuficiente && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
            {[
              { label: "Vitórias", value: competitor.data.total_vitorias },
              { label: "Taxa de Vitória", value: `${competitor.data.taxa_vitoria_pct?.toFixed(1)}%` },
              { label: "Preço Médio", value: brl(competitor.data.preco_medio_brl) },
              { label: "Dominante", value: competitor.data.dominante ? "Sim" : "Não" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-zinc-800 rounded-xl p-3">
                <p className="text-xs text-zinc-500 mb-1">{label}</p>
                <p className="text-lg font-bold text-zinc-100">{value}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Benchmark de Preço ── */}
      <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 text-zinc-300 font-semibold">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          Benchmark de Preço
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Descrição do item ou serviço"
            value={itemInput}
            onChange={(e) => setItemInput(e.target.value)}
          />
          <button
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-4 rounded-lg transition"
            onClick={() => setItem(itemInput)}
          >
            Buscar
          </button>
        </div>

        {benchmark.isLoading && <p className="text-zinc-500 text-sm">Carregando…</p>}
        {benchmark.data && benchmark.data.data_insuficiente && (
          <InsuficienteCard label="Benchmark" />
        )}
        {benchmark.data && !benchmark.data.data_insuficiente && (
          <div className="grid grid-cols-3 md:grid-cols-5 gap-3 pt-2">
            {[
              { label: "Mín", value: brl(benchmark.data.min_brl) },
              { label: "P25", value: brl(benchmark.data.percentil_25) },
              { label: "Média", value: brl(benchmark.data.media_brl) },
              { label: "P75", value: brl(benchmark.data.percentil_75) },
              { label: "Máx", value: brl(benchmark.data.max_brl) },
            ].map(({ label, value }) => (
              <div key={label} className="bg-zinc-800 rounded-xl p-3 text-center">
                <p className="text-xs text-zinc-500 mb-1">{label}</p>
                <p className="text-sm font-bold text-zinc-100">{value}</p>
              </div>
            ))}
          </div>
        )}
        {benchmark.data && benchmark.data.tendencia_12m_pct != null && (
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <TrendingUp className="w-4 h-4" />
            Tendência 12m: {benchmark.data.tendencia_12m_pct > 0 ? "+" : ""}
            {benchmark.data.tendencia_12m_pct?.toFixed(1)}%
          </div>
        )}
      </section>

      {/* ── Score de Órgão ── */}
      <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 text-zinc-300 font-semibold">
          <Building2 className="w-5 h-5 text-emerald-400" />
          Score de Órgão Pagador
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="Código UASG"
            value={uasgInput}
            onChange={(e) => setUasgInput(e.target.value)}
          />
          <button
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold px-4 rounded-lg transition"
            onClick={() => setUasg(uasgInput)}
          >
            Consultar
          </button>
        </div>

        {organ.isLoading && <p className="text-zinc-500 text-sm">Carregando…</p>}
        {organ.data && organ.data.data_insuficiente && (
          <InsuficienteCard label="Órgão" />
        )}
        {organ.data && !organ.data.data_insuficiente && (
          <div className="flex items-start gap-8 pt-2">
            <ScoreGauge score={organ.data.score} label={organ.data.label} />
            <div className="space-y-2 flex-1">
              {organ.data.orgao_nome && (
                <p className="text-zinc-200 font-medium">{organ.data.orgao_nome}</p>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-zinc-800 rounded-xl p-3">
                  <p className="text-xs text-zinc-500 mb-1">Prazo Médio Pgto</p>
                  <p className="font-bold text-zinc-100">
                    {organ.data.prazo_medio_pagamento_dias ?? "—"} dias
                  </p>
                </div>
                <div className="bg-zinc-800 rounded-xl p-3">
                  <p className="text-xs text-zinc-500 mb-1">Inadimplência</p>
                  <p className="font-bold text-zinc-100">
                    {organ.data.indice_inadimplencia_pct?.toFixed(1) ?? "0"}%
                  </p>
                </div>
              </div>
              {organ.data.alerta_inadimplencia && (
                <div className="flex items-center gap-2 bg-red-900/20 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  Órgão com histórico de inadimplência — atenção ao fluxo de caixa
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Resumo do Nicho ── */}
      <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 text-zinc-300 font-semibold">
          <ShieldCheck className="w-5 h-5 text-amber-400" />
          Resumo do Nicho (Concentração)
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
            placeholder="Código CNAE (ex: 6201-5)"
            value={segInput}
            onChange={(e) => setSegInput(e.target.value)}
          />
          <button
            className="bg-amber-600 hover:bg-amber-500 text-white text-sm font-semibold px-4 rounded-lg transition"
            onClick={() => setSegmento(segInput)}
          >
            Analisar
          </button>
        </div>

        {summary.isLoading && <p className="text-zinc-500 text-sm">Carregando…</p>}
        {summary.data && (
          <>
            {summary.data.concentracao_alta && (
              <div className="flex items-center gap-2 bg-amber-900/20 border border-amber-500/30 rounded-lg p-3 text-sm text-amber-300">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                Mercado concentrado — CNPJ dominante: {summary.data.cnpj_dominante}
              </div>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-zinc-300">
                <thead>
                  <tr className="text-xs text-zinc-500 border-b border-zinc-800">
                    <th className="text-left py-2 pr-4">Fornecedor</th>
                    <th className="text-right py-2 pr-4">Contratos</th>
                    <th className="text-right py-2">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.top_fornecedores?.map((f: any) => (
                    <tr key={f.cnpj} className="border-b border-zinc-800/50">
                      <td className="py-2 pr-4">
                        <p className="font-medium text-zinc-100">{f.nome || "—"}</p>
                        <p className="text-xs text-zinc-500">{f.cnpj}</p>
                      </td>
                      <td className="text-right py-2 pr-4">{f.total_contratos}</td>
                      <td className="text-right py-2">{f.share_pct?.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
