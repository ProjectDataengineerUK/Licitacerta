"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  FileSearch,
  TrendingUp,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Gavel,
  ChevronRight,
  Plus,
} from "lucide-react";
import { api } from "@/lib/api";
import { SubmitForm } from "@/components/SubmitForm";
import { TERMINAL_STEPS } from "@/lib/types";
import type { RunStatus } from "@/lib/types";

/* ─── decision meta ─────────────────────────────────────────────────── */
const DEC = {
  participar:           { label: "Participar",     color: "#22c55e", ring: "#16a34a", bg: "bg-green-500/10",  text: "text-green-400",  Icon: CheckCircle2 },
  nao_participar:       { label: "Não Participar", color: "#ef4444", ring: "#dc2626", bg: "bg-red-500/10",    text: "text-red-400",    Icon: XCircle },
  pedir_esclarecimento: { label: "Esclarecimento", color: "#f59e0b", ring: "#d97706", bg: "bg-amber-500/10",  text: "text-amber-400",  Icon: HelpCircle },
  impugnar:             { label: "Impugnar",        color: "#f97316", ring: "#ea580c", bg: "bg-orange-500/10", text: "text-orange-400", Icon: Gavel },
} as const;

/* ─── Donut SVG ──────────────────────────────────────────────────────── */
function DonutChart({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((s, n) => s + n, 0);
  if (total === 0) {
    return (
      <div className="w-32 h-32 rounded-full border-2 border-dashed border-zinc-700 flex items-center justify-center">
        <span className="text-xs text-zinc-600">sem dados</span>
      </div>
    );
  }

  const R = 52, cx = 64, cy = 64, stroke = 20;
  const circ = 2 * Math.PI * R;
  let offset = 0;

  const slices = Object.entries(DEC).map(([key, meta]) => {
    const count = counts[key] ?? 0;
    const pct = count / total;
    const dash = pct * circ;
    const gap = circ - dash;
    const slice = { key, color: meta.color, dash, gap, offset };
    offset += dash;
    return slice;
  });

  return (
    <svg width="128" height="128" viewBox="0 0 128 128">
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="#27272a" strokeWidth={stroke} />
      {slices.map((s) => (
        <circle
          key={s.key}
          cx={cx} cy={cy} r={R}
          fill="none"
          stroke={s.color}
          strokeWidth={stroke}
          strokeDasharray={`${s.dash} ${s.gap}`}
          strokeDashoffset={-s.offset + circ / 4}
          strokeLinecap="butt"
        />
      ))}
      <text x={cx} y={cy - 6} textAnchor="middle" fill="#f4f4f5" fontSize="22" fontWeight="700">{total}</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#71717a" fontSize="10">análises</text>
    </svg>
  );
}

/* ─── KPI card ───────────────────────────────────────────────────────── */
function KpiCard({
  label, value, sub, Icon, accent, href,
}: {
  label: string;
  value: string | number;
  sub?: string;
  Icon: React.ElementType;
  accent: string;
  href?: string;
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

/* ─── Run row ────────────────────────────────────────────────────────── */
function RunRow({ run }: { run: RunStatus }) {
  const router = useRouter();
  const rec = run.bid_decision?.recommendation as keyof typeof DEC | undefined;
  const meta = rec ? DEC[rec] : null;

  return (
    <li
      onClick={() =>
        router.push(
          TERMINAL_STEPS.has(run.current_step)
            ? `/runs/${run.run_id}/result`
            : `/runs/${run.run_id}`
        )
      }
      className="flex items-center gap-3 px-5 py-3.5 hover:bg-zinc-800/60 cursor-pointer transition-colors group"
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${meta ? meta.bg : "bg-zinc-800"}`}>
        {meta ? (
          <meta.Icon className={`w-4 h-4 ${meta.text}`} />
        ) : (
          <Clock className="w-4 h-4 text-zinc-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono text-zinc-300 truncate">{run.edital_id.slice(0, 28)}…</p>
        {run.bid_decision?.summary && (
          <p className="text-xs text-zinc-500 truncate mt-0.5">{run.bid_decision.summary}</p>
        )}
      </div>
      {meta && (
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full flex-shrink-0 ${meta.bg} ${meta.text}`}>
          {meta.label}
        </span>
      )}
      <ChevronRight className="w-4 h-4 text-zinc-700 group-hover:text-zinc-400 flex-shrink-0 transition-colors" />
    </li>
  );
}

/* ─── Main ───────────────────────────────────────────────────────────── */
export function DashboardHome() {
  const { data: runs } = useQuery({
    queryKey: ["runs"],
    queryFn: () => api.listRuns(),
    refetchInterval: 30_000,
  });

  const { data: hitl } = useQuery({
    queryKey: ["hitl"],
    queryFn: () => api.listHITL(),
    refetchInterval: 30_000,
  });

  const { data: certData } = useQuery({
    queryKey: ["certidoes"],
    queryFn: () => api.listCertidoes(),
    refetchInterval: 60_000,
  });

  const allRuns = runs ?? [];
  const decided = allRuns.filter((r) => r.bid_decision?.recommendation);

  const decCounts: Record<string, number> = {};
  for (const r of decided) {
    const k = r.bid_decision!.recommendation;
    decCounts[k] = (decCounts[k] ?? 0) + 1;
  }

  const participar = decCounts["participar"] ?? 0;
  const participRate = decided.length > 0 ? Math.round((participar / decided.length) * 100) : null;

  const pendingHITL = hitl?.items.filter((i) => i.status === "pending").length ?? 0;
  const certAlert = (certData?.certidoes ?? []).filter(
    (c) => c.status === "expired" || c.status === "expiring_soon"
  ).length;

  const recent = allRuns.slice(0, 7);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-blue-600 via-blue-700 to-violet-700 p-7 text-white shadow-2xl shadow-blue-900/30">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-blue-200 text-sm font-medium mb-1">Bem-vindo ao</p>
            <h1 className="text-3xl font-bold tracking-tight">LicitaCerta AI</h1>
            <p className="text-blue-200 mt-2 text-sm max-w-md">
              Plataforma de análise inteligente de editais.{" "}
              {allRuns.length > 0
                ? `${allRuns.length} análise${allRuns.length > 1 ? "s" : ""} processada${allRuns.length > 1 ? "s" : ""}.`
                : "Envie seu primeiro edital para começar."}
            </p>
          </div>
          <Link
            href="#nova-analise"
            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-sm px-4 py-2.5 rounded-xl transition-colors flex-shrink-0 backdrop-blur-sm"
          >
            <Plus className="w-4 h-4" />
            Nova análise
          </Link>
        </div>

        {(pendingHITL > 0 || certAlert > 0) && (
          <div className="flex flex-wrap gap-2 mt-5">
            {pendingHITL > 0 && (
              <Link
                href="/hitl"
                className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors border border-white/10"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-orange-300 animate-pulse" />
                {pendingHITL} aprovação{pendingHITL > 1 ? "ões" : ""} pendente{pendingHITL > 1 ? "s" : ""}
              </Link>
            )}
            {certAlert > 0 && (
              <Link
                href="/certidoes"
                className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors border border-white/10"
              >
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-300" />
                {certAlert} certidão{certAlert > 1 ? "ões" : ""} em alerta
              </Link>
            )}
          </div>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total de análises"
          value={allRuns.length}
          sub="histórico completo"
          Icon={FileSearch}
          accent="bg-blue-500/15 text-blue-400"
        />
        <KpiCard
          label="Taxa de participação"
          value={participRate !== null ? `${participRate}%` : "—"}
          sub={decided.length > 0 ? `${decided.length} com decisão` : "sem decisões"}
          Icon={TrendingUp}
          accent={participRate !== null && participRate >= 50 ? "bg-green-500/15 text-green-400" : "bg-zinc-700 text-zinc-400"}
        />
        <KpiCard
          label="Aprovações pendentes"
          value={pendingHITL}
          sub="aguardando revisão"
          Icon={Clock}
          accent={pendingHITL > 0 ? "bg-orange-500/15 text-orange-400" : "bg-zinc-700 text-zinc-400"}
          href={pendingHITL > 0 ? "/hitl" : undefined}
        />
        <KpiCard
          label="Certidões em alerta"
          value={certAlert}
          sub="vencidas ou a vencer"
          Icon={AlertTriangle}
          accent={certAlert > 0 ? "bg-red-500/15 text-red-400" : "bg-zinc-700 text-zinc-400"}
          href={certAlert > 0 ? "/certidoes" : undefined}
        />
      </div>

      {/* Middle grid: donut + recent */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Donut chart */}
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <h2 className="text-sm font-semibold text-zinc-300 mb-5">Distribuição de decisões</h2>
          <div className="flex items-center gap-6">
            <DonutChart counts={decCounts} />
            <div className="space-y-2.5 flex-1">
              {Object.entries(DEC).map(([key, meta]) => {
                const count = decCounts[key] ?? 0;
                const pct = decided.length > 0 ? Math.round((count / decided.length) * 100) : 0;
                return (
                  <div key={key} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: meta.color }} />
                    <span className="text-xs text-zinc-400 flex-1 truncate">{meta.label}</span>
                    <span className="text-xs font-bold text-zinc-200">{count}</span>
                    <span className="text-xs text-zinc-600 w-8 text-right">{pct}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Recent runs */}
        <div className="lg:col-span-2 bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-300">Análises recentes</h2>
            <Link href="/runs" className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition-colors">
              Ver todas <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          {recent.length === 0 ? (
            <div className="py-14 text-center">
              <FileSearch className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-500 text-sm">Nenhuma análise ainda.</p>
              <p className="text-zinc-600 text-xs mt-1">Use o formulário abaixo para começar.</p>
            </div>
          ) : (
            <ul className="divide-y divide-zinc-800/60">
              {recent.map((run) => <RunRow key={run.run_id} run={run} />)}
            </ul>
          )}
        </div>
      </div>

      {/* New analysis form */}
      <div id="nova-analise" className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
            <Plus className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-zinc-100">Nova análise de edital</h2>
            <p className="text-xs text-zinc-500">Cole o texto do edital e informe o CNPJ da sua empresa</p>
          </div>
        </div>
        <SubmitForm />
      </div>
    </div>
  );
}
