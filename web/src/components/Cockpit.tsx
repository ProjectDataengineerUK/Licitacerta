"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  FileSearch, TrendingUp, AlertTriangle, Wallet, Plus, ChevronRight,
  Activity, Kanban,
} from "lucide-react";
import { api } from "@/lib/api";
import { STAGE_LABELS, STAGE_ORDER } from "@/lib/types";
import type { PipelineStage } from "@/lib/types";

/* ─── KPI card ───────────────────────────────────────────────────────── */
function KpiCard({
  label, value, sub, Icon, accent, href,
}: {
  label: string; value: string | number; sub?: string;
  Icon: React.ElementType; accent: string; href?: string;
}) {
  const inner = (
    <div className={`bg-zinc-900 rounded-2xl border border-zinc-800 p-5 flex items-start gap-4 hover:border-zinc-700 transition-colors ${href ? "cursor-pointer" : ""}`}>
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${accent}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide mb-0.5">{label}</p>
        <p className="text-3xl font-bold text-zinc-100 leading-none">{value}</p>
        {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
      </div>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function brl(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

const HEALTH_COLOR = (score: number) =>
  score >= 70 ? "text-green-400" : score >= 40 ? "text-amber-400" : "text-red-400";

/* ─── Cockpit ────────────────────────────────────────────────────────── */
export function Cockpit() {
  const { data: summary } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.getDashboardSummary(),
    refetchInterval: 30_000,
  });

  const { data: health } = useQuery({
    queryKey: ["health-score"],
    queryFn: () => api.getHealthScore(),
    refetchInterval: 60_000,
  });

  const pipeline = summary?.pipeline;
  const totalPipeline = pipeline
    ? pipeline.analisando + pipeline.decidindo + pipeline.preparando + pipeline.disputando
    : 0;

  const counts: Record<PipelineStage, number> = {
    analisando: pipeline?.analisando ?? 0,
    decidindo: pipeline?.decidindo ?? 0,
    preparando: pipeline?.preparando ?? 0,
    disputando: pipeline?.disputando ?? 0,
    ganho: pipeline?.ganho_mes ?? 0,
    perdido: pipeline?.perdido_mes ?? 0,
  };

  const criticos = summary?.alertas_criticos ?? 0;
  const warnings = summary?.alertas_warning ?? 0;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-blue-600 via-blue-700 to-violet-700 p-7 text-white shadow-2xl shadow-blue-900/30">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-blue-200 text-sm font-medium mb-1">Bem-vindo ao</p>
            <h1 className="text-3xl font-bold tracking-tight">LicitaCerta AI</h1>
            <p className="text-blue-200 mt-2 text-sm max-w-md">
              Cockpit de operação: pipeline, caixa e alertas em um só lugar.
            </p>
          </div>
          <Link
            href="/submit"
            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors flex-shrink-0 backdrop-blur-sm"
          >
            <Plus className="w-4 h-4" />
            Nova análise
          </Link>
        </div>

        {(criticos > 0 || warnings > 0) && (
          <div className="flex flex-wrap gap-2 mt-5">
            <Link
              href="/alertas"
              className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors border border-white/10"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-300" />
              {criticos} crítico{criticos !== 1 ? "s" : ""} · {warnings} alerta{warnings !== 1 ? "s" : ""}
            </Link>
          </div>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Em disputa"
          value={totalPipeline}
          sub="no pipeline ativo"
          Icon={FileSearch}
          accent="bg-blue-500/15 text-blue-400"
          href="/pipeline"
        />
        <KpiCard
          label="Taxa de vitória"
          value={summary ? `${Math.round(summary.taxa_vitoria_pct)}%` : "—"}
          sub="no mês"
          Icon={TrendingUp}
          accent={(summary?.taxa_vitoria_pct ?? 0) >= 50 ? "bg-green-500/15 text-green-400" : "bg-zinc-700 text-zinc-400"}
        />
        <KpiCard
          label="Receita projetada"
          value={summary ? brl(summary.financeiro.receita_contratada_brl) : "—"}
          sub="contratada"
          Icon={Wallet}
          accent="bg-emerald-500/15 text-emerald-400"
          href="/financeiro"
        />
        <KpiCard
          label="Alertas críticos"
          value={criticos}
          sub="precisam de ação"
          Icon={AlertTriangle}
          accent={criticos > 0 ? "bg-red-500/15 text-red-400" : "bg-zinc-700 text-zinc-400"}
          href={criticos > 0 ? "/alertas" : undefined}
        />
      </div>

      {/* Pipeline resumido + Health score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline resumo */}
        <div className="lg:col-span-2 bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
              <Kanban className="w-4 h-4 text-zinc-500" /> Pipeline
            </h2>
            <Link href="/pipeline" className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition-colors">
              Abrir board <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 divide-x divide-zinc-800/60">
            {STAGE_ORDER.map((stage) => (
              <div key={stage} className="px-3 py-4 text-center">
                <p className="text-2xl font-bold text-zinc-100">{counts[stage]}</p>
                <p className="text-[11px] text-zinc-500 mt-1 truncate">{STAGE_LABELS[stage]}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Health score */}
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <h2 className="text-sm font-semibold text-zinc-300 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-zinc-500" /> Saúde operacional
          </h2>
          {health ? (
            <div className="flex items-center gap-5">
              <div className={`text-5xl font-bold ${HEALTH_COLOR(health.score)}`}>{health.score}</div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-zinc-200 capitalize">{health.label}</p>
                {health.delta_semana != null && (
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {health.delta_semana >= 0 ? "+" : ""}{health.delta_semana} vs. semana passada
                  </p>
                )}
                {health.recomendacoes?.[0] && (
                  <p className="text-xs text-zinc-500 mt-2 line-clamp-2">
                    {health.recomendacoes[0].titulo ?? health.recomendacoes[0].texto}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-zinc-600 text-sm">Sem dados de saúde ainda.</p>
          )}
        </div>
      </div>
    </div>
  );
}
