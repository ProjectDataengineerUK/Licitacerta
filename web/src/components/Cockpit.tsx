"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TooltipProps } from "recharts";
import {
  AlertTriangle, ChevronRight, ArrowUpRight, ArrowDownRight,
  Clock, CheckCircle, Plus, Zap, TrendingUp, Wallet, Activity,
  FileSearch, Radar, BarChart3,
} from "lucide-react";
import { api } from "@/lib/api";
import { STAGE_LABELS, STAGE_ORDER } from "@/lib/types";
import type { FinanceiroTrend, PipelineStage } from "@/lib/types";

// ── formatting ────────────────────────────────────────────────────────────────

function brl(v: number): string {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(0)}k`;
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

// ── chart data real — GET /financeiro/trend ──────────────────────────────────

const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

function trendToChart(trend: FinanceiroTrend | undefined) {
  if (!trend) return [];
  return trend.months.map((m) => ({
    month: MESES[parseInt(m.mes.slice(5), 10) - 1] ?? m.mes,
    receita: m.contratado_brl,
    receber: m.a_receber_brl,
  }));
}

// ── stage colors ──────────────────────────────────────────────────────────────

const STAGE_COLORS: Record<PipelineStage, string> = {
  analisando: "#3b82f6",
  decidindo:  "#8b5cf6",
  preparando: "#f59e0b",
  disputando: "#ef4444",
  ganho:      "#10b981",
  perdido:    "#52525b",
};

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, icon: Icon, iconColor, trend, href,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  iconColor: string;
  trend?: { dir: "up" | "down" | "flat"; text: string };
  href?: string;
}) {
  const TrendIcon = trend?.dir === "up" ? ArrowUpRight : trend?.dir === "down" ? ArrowDownRight : null;
  const trendCls = trend?.dir === "up" ? "text-emerald-400" : trend?.dir === "down" ? "text-red-400" : "text-zinc-500";

  const card = (
    <div className={`group bg-zinc-900 rounded-2xl p-5 ring-1 ring-zinc-800/80 hover:ring-zinc-700 transition-all duration-200 ${href ? "cursor-pointer" : ""}`}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-zinc-500">{label}</p>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconColor}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-[28px] font-bold text-zinc-100 leading-none">{value}</p>
      <div className="flex items-center gap-1.5 mt-2">
        {sub && <p className="text-xs text-zinc-500">{sub}</p>}
        {trend && TrendIcon && (
          <span className={`flex items-center gap-0.5 text-xs font-medium ${trendCls}`}>
            <TrendIcon className="w-3.5 h-3.5" />{trend.text}
          </span>
        )}
      </div>
    </div>
  );
  return href ? <Link href={href}>{card}</Link> : card;
}

// ── pipeline stage bar ────────────────────────────────────────────────────────

function StageRow({ stage, count, max }: { stage: PipelineStage; count: number; max: number }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0;
  const color = STAGE_COLORS[stage];
  return (
    <div className="flex items-center gap-3">
      <p className="w-[84px] text-[12px] text-zinc-500 text-right shrink-0">{STAGE_LABELS[stage]}</p>
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <p className="w-6 text-[12px] font-semibold text-zinc-300 text-right shrink-0">{count}</p>
    </div>
  );
}

// ── health score SVG gauge ────────────────────────────────────────────────────

function HealthGauge({ score, label, delta }: { score: number; label: string; delta?: number | null }) {
  const r = 36, cx = 55, cy = 56;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75;
  const progress = arcLen * Math.max(0, Math.min(100, score)) / 100;
  const color = score >= 70 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative">
        <svg width="110" height="92" viewBox="0 0 110 92">
          <circle cx={cx} cy={cy} r={r} fill="none" stroke="#3f3f46" strokeWidth={7}
            strokeDasharray={`${arcLen} ${circ - arcLen}`} strokeLinecap="round"
            transform={`rotate(135 ${cx} ${cy})`}
          />
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={7}
            strokeDasharray={`${progress} ${circ - progress}`} strokeLinecap="round"
            transform={`rotate(135 ${cx} ${cy})`}
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pb-1">
          <span className="text-[26px] font-bold leading-none" style={{ color }}>{score}</span>
          <span className="text-[10px] text-zinc-500 capitalize mt-0.5">{label}</span>
        </div>
      </div>
      {delta != null && (
        <p className={`text-xs font-medium flex items-center gap-1 ${delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {delta >= 0 ? "▲" : "▼"} {Math.abs(delta)} pts esta semana
        </p>
      )}
    </div>
  );
}

// ── chart tooltip ─────────────────────────────────────────────────────────────

function ChartTooltipContent({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const labels: Record<string, string> = { receita: "Receita contratada", receber: "A receber" };
  return (
    <div className="bg-zinc-800 border border-zinc-700/80 rounded-xl px-4 py-3 shadow-2xl shadow-black/40 text-sm">
      <p className="text-xs font-semibold text-zinc-400 mb-2">{String(label ?? "")}</p>
      {payload.map((p) => (
        <p key={String(p.dataKey)} className="font-semibold" style={{ color: p.color }}>
          {labels[String(p.dataKey)] ?? p.dataKey}: {brl(p.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

// ── main cockpit ──────────────────────────────────────────────────────────────

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

  const { data: hitlData } = useQuery({
    queryKey: ["hitl"],
    queryFn: () => api.listHITL(),
    refetchInterval: 15_000,
  });

  const { data: trend } = useQuery({
    queryKey: ["financeiro-trend"],
    queryFn: () => api.getFinanceiroTrend(),
    refetchInterval: 60_000,
  });

  const { data: predictions } = useQuery({
    queryKey: ["radar-predictions"],
    queryFn: () => api.listPredictions(),
    refetchInterval: 120_000,
  });

  const pipeline = summary?.pipeline;
  const counts: Record<PipelineStage, number> = {
    analisando: pipeline?.analisando ?? 0,
    decidindo:  pipeline?.decidindo  ?? 0,
    preparando: pipeline?.preparando ?? 0,
    disputando: pipeline?.disputando ?? 0,
    ganho:      pipeline?.ganho_mes  ?? 0,
    perdido:    pipeline?.perdido_mes ?? 0,
  };
  const totalActive = counts.analisando + counts.decidindo + counts.preparando + counts.disputando;
  const maxCount = Math.max(...Object.values(counts), 1);
  const criticos = summary?.alertas_criticos ?? 0;
  const pendingHITL = hitlData?.items.filter((i) => i.status === "pending") ?? [];
  const chartData = trendToChart(trend);
  const hasTrendData = chartData.some((m) => m.receita > 0 || m.receber > 0);
  const radarAtivo = predictions?.filter((p) => p.status === "ativa" || p.status === "active") ?? predictions ?? [];

  const today = new Date().toLocaleDateString("pt-BR", {
    weekday: "long", day: "numeric", month: "long",
  });

  return (
    <div className="space-y-6 max-w-[1300px]">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Cockpit</h1>
          <p className="text-sm text-zinc-500 mt-0.5 capitalize">{today}</p>
        </div>
        <Link
          href="/submit"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors shadow-lg shadow-blue-600/20"
        >
          <Plus className="w-4 h-4" />
          Nova análise
        </Link>
      </div>

      {/* ── Critical banner ── */}
      {criticos > 0 && (
        <Link
          href="/alertas"
          className="flex items-center gap-3 bg-red-500/8 border border-red-500/20 rounded-xl px-4 py-3 hover:bg-red-500/12 transition-colors group"
        >
          <div className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <p className="text-sm text-red-300 font-medium flex-1">
            {criticos} alerta{criticos !== 1 ? "s" : ""} crítico{criticos !== 1 ? "s" : ""} precisando de ação imediata
          </p>
          <ChevronRight className="w-4 h-4 text-red-400/60 group-hover:text-red-400 transition-colors shrink-0" />
        </Link>
      )}

      {/* ── KPI strip ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        <KpiCard
          label="Pipeline ativo"
          value={totalActive}
          sub="licitações em curso"
          icon={FileSearch}
          iconColor="bg-blue-500/15 text-blue-400"
          trend={{ dir: totalActive > 0 ? "up" : "flat", text: "ao vivo" }}
          href="/pipeline"
        />
        <KpiCard
          label="Taxa de vitória"
          value={summary ? `${Math.round(summary.taxa_vitoria_pct)}%` : "—"}
          sub="este mês"
          icon={TrendingUp}
          iconColor={(summary?.taxa_vitoria_pct ?? 0) >= 50 ? "bg-emerald-500/15 text-emerald-400" : "bg-zinc-700 text-zinc-500"}
          trend={summary && summary.taxa_vitoria_pct >= 50
            ? { dir: "up", text: "acima da média" }
            : undefined}
        />
        <KpiCard
          label="Receita contratada"
          value={summary ? brl(summary.financeiro.receita_contratada_brl) : "—"}
          sub="total acumulado"
          icon={Wallet}
          iconColor="bg-emerald-500/15 text-emerald-400"
          href="/financeiro"
        />
        <KpiCard
          label="A receber (30d)"
          value={summary ? brl(summary.financeiro.a_receber_30d_brl) : "—"}
          sub="próximos 30 dias"
          icon={Wallet}
          iconColor="bg-amber-500/15 text-amber-400"
          trend={{ dir: "up", text: "em prazo" }}
          href="/financeiro"
        />
        <KpiCard
          label="Alertas críticos"
          value={criticos}
          sub={criticos > 0 ? "precisam de ação" : "tudo em ordem"}
          icon={AlertTriangle}
          iconColor={criticos > 0 ? "bg-red-500/15 text-red-400" : "bg-zinc-700 text-zinc-500"}
          trend={criticos > 0 ? { dir: "down", text: "atenção" } : { dir: "up", text: "ok" }}
          href={criticos > 0 ? "/alertas" : undefined}
        />
      </div>

      {/* ── Main row: chart + pipeline ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* Revenue AreaChart */}
        <div className="xl:col-span-2 bg-zinc-900 rounded-2xl ring-1 ring-zinc-800/80 p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">Desempenho financeiro</h2>
              <p className="text-xs text-zinc-500 mt-0.5">Receita contratada e valores a receber</p>
            </div>
            <Link href="/financeiro" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Detalhar <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {!hasTrendData && (
            <div className="h-[196px] flex flex-col items-center justify-center text-center">
              <BarChart3 className="w-8 h-8 text-zinc-700 mb-2" />
              <p className="text-sm text-zinc-500">Sem contratos registrados ainda</p>
              <p className="text-xs text-zinc-600 mt-1">A série real aparece aqui quando o primeiro contrato for cadastrado</p>
            </div>
          )}
          {hasTrendData && (
          <ResponsiveContainer width="100%" height={196}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gReceita" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gReceber" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.24} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false} tickLine={false}
              />
              <YAxis
                tick={{ fill: "#71717a", fontSize: 11 }}
                axisLine={false} tickLine={false}
                tickFormatter={(v: number) => v >= 1000 ? `${Math.round(v / 1000)}k` : String(v)}
              />
              <Tooltip content={<ChartTooltipContent />}
              />
              <Area
                type="monotone" dataKey="receita"
                stroke="#3b82f6" strokeWidth={2}
                fill="url(#gReceita)" dot={false} activeDot={{ r: 4, strokeWidth: 0 }}
              />
              <Area
                type="monotone" dataKey="receber"
                stroke="#10b981" strokeWidth={2}
                fill="url(#gReceber)" dot={false} activeDot={{ r: 4, strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
          )}
          <div className="flex items-center gap-5 mt-4 pt-4 border-t border-zinc-800/60">
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-blue-500 rounded-full" />
              <span className="text-xs text-zinc-500">Receita contratada</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-emerald-500 rounded-full" />
              <span className="text-xs text-zinc-500">A receber</span>
            </div>
          </div>
        </div>

        {/* Pipeline stages */}
        <div className="bg-zinc-900 rounded-2xl ring-1 ring-zinc-800/80 p-6 flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-semibold text-zinc-200">Pipeline</h2>
              <p className="text-xs text-zinc-500 mt-0.5">{totalActive} em disputa agora</p>
            </div>
            <Link href="/pipeline" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Board <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="flex-1 flex flex-col justify-center space-y-3.5">
            {STAGE_ORDER.map((stage) => (
              <StageRow key={stage} stage={stage} count={counts[stage]} max={maxCount} />
            ))}
          </div>
        </div>
      </div>

      {/* ── Mercado & Radar ── */}
      <div className="bg-zinc-900 rounded-2xl ring-1 ring-zinc-800/80 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">Inteligência de mercado</h2>
            <p className="text-xs text-zinc-500 mt-0.5">Radar de intenção de compra e raio-X competitivo</p>
          </div>
          <Link href="/mercado" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors">
            Raio-X completo <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0">
              <Radar className="w-4.5 h-4.5 text-violet-400" />
            </div>
            <div>
              <p className="text-lg font-bold text-zinc-100">{radarAtivo.length}</p>
              <p className="text-xs text-zinc-500">editais previstos pelo Radar</p>
            </div>
          </div>
          {radarAtivo.length > 0 ? (
            <div className="sm:col-span-2 min-w-0">
              <p className="text-xs text-zinc-500 mb-1">Próxima oportunidade prevista</p>
              <p className="text-sm text-zinc-200 truncate">
                {radarAtivo[0].objeto_previsto ?? "Objeto a confirmar"}
                {radarAtivo[0].orgao_nome ? ` — ${radarAtivo[0].orgao_nome}` : ""}
              </p>
              <p className="text-xs text-zinc-500 mt-0.5">
                {new Date(radarAtivo[0].data_prevista_publicacao).toLocaleDateString("pt-BR")} · confiança {Math.round(radarAtivo[0].confianca_pct)}%
              </p>
            </div>
          ) : (
            <div className="sm:col-span-2 flex items-center">
              <p className="text-sm text-zinc-500">Nenhuma predição ativa — o Radar varre os Planos de Contratação Anual (PCA) do PNCP</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Bottom row: HITL + health ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* HITL queue */}
        <div className="xl:col-span-2 bg-zinc-900 rounded-2xl ring-1 ring-zinc-800/80 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60">
            <div className="flex items-center gap-2.5">
              <h2 className="text-sm font-semibold text-zinc-200">Aprovações pendentes</h2>
              {pendingHITL.length > 0 && (
                <span className="bg-orange-500 text-white text-[10px] font-bold rounded-full px-2 py-0.5 leading-snug">
                  {pendingHITL.length}
                </span>
              )}
            </div>
            <Link href="/hitl" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Ver todas <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {pendingHITL.length === 0 ? (
            <div className="px-6 py-12 flex flex-col items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <p className="text-sm text-zinc-500">Nenhuma aprovação pendente</p>
              <p className="text-xs text-zinc-600">O pipeline está fluindo sem intervenção humana</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/50">
              {pendingHITL.slice(0, 4).map((item) => {
                const hoursLeft = Math.max(0, Math.floor((new Date(item.expires_at).getTime() - Date.now()) / 3_600_000));
                const urgent = hoursLeft < 4;
                return (
                  <Link
                    key={item.id}
                    href="/hitl"
                    className="flex items-start gap-4 px-6 py-4 hover:bg-zinc-800/40 transition-colors group"
                  >
                    <div className={`w-2 h-2 rounded-full mt-2 shrink-0 ${urgent ? "bg-red-400 animate-pulse" : "bg-orange-400"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-zinc-200 truncate">{item.action_required}</p>
                      <p className={`text-xs mt-0.5 flex items-center gap-1.5 ${urgent ? "text-red-400" : "text-zinc-500"}`}>
                        <Clock className="w-3 h-3" />
                        {hoursLeft === 0 ? "Expirando agora" : `Expira em ${hoursLeft}h`}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 shrink-0 mt-0.5 transition-colors" />
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Health score */}
        <div className="bg-zinc-900 rounded-2xl ring-1 ring-zinc-800/80 p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-zinc-200">Saúde operacional</h2>
            <Activity className="w-4 h-4 text-zinc-600" />
          </div>

          {health ? (
            <div className="flex-1 flex flex-col items-center justify-between gap-4">
              <HealthGauge score={health.score} label={health.label} delta={health.delta_semana} />
              <div className="w-full space-y-2">
                {health.componentes?.slice(0, 3).map((c) => (
                  <div key={c.nome} className="flex items-center gap-2.5">
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] text-zinc-500 truncate">{c.nome}</p>
                    </div>
                    <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden shrink-0">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${c.score}%`,
                          backgroundColor: c.score >= 70 ? "#10b981" : c.score >= 40 ? "#f59e0b" : "#ef4444",
                        }}
                      />
                    </div>
                    <span className="text-[11px] font-semibold text-zinc-400 w-6 text-right shrink-0">{c.score}</span>
                  </div>
                ))}
              </div>
              {health.recomendacoes?.[0] && (
                <div className="w-full bg-zinc-800/50 rounded-xl px-4 py-3 ring-1 ring-zinc-700/40">
                  <p className="text-xs text-zinc-400 leading-relaxed line-clamp-3">
                    {health.recomendacoes[0].titulo ?? health.recomendacoes[0].texto}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-3">
              <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center">
                <Zap className="w-5 h-5 text-zinc-600" />
              </div>
              <p className="text-xs text-zinc-600 text-center">Calculando saúde<br />operacional…</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
