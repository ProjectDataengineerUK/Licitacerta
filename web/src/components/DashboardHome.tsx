"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SubmitForm } from "@/components/SubmitForm";
import { TERMINAL_STEPS } from "@/lib/types";
import type { RunStatus } from "@/lib/types";

const REC_LABEL: Record<string, string> = {
  participar: "Participar",
  nao_participar: "Não Participar",
  pedir_esclarecimento: "Esclarecimento",
  impugnar: "Impugnar",
};

const REC_COLOR: Record<string, string> = {
  participar: "text-green-600 bg-green-50",
  nao_participar: "text-red-600 bg-red-50",
  pedir_esclarecimento: "text-yellow-700 bg-yellow-50",
  impugnar: "text-orange-600 bg-orange-50",
};

const STEP_LABEL: Record<string, string> = {
  completed: "Concluído",
  decided: "Aguard. aprovação",
  rejected: "Rejeitado",
  subgraph_ingestion: "Lendo edital",
  subgraph_understanding: "Entendendo",
  subgraph_validation: "Validando",
  subgraph_decision: "Decidindo",
  subgraph_execution: "Gerando proposta",
  subgraph_post_award: "Pós-vitória",
};

function stepColor(step: string): string {
  if (step === "completed") return "text-green-700 bg-green-50";
  if (step === "decided") return "text-orange-700 bg-orange-50";
  if (step.includes("failed") || step === "rejected") return "text-red-700 bg-red-50";
  return "text-blue-700 bg-blue-50";
}

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-white rounded-xl border p-5 shadow-sm flex flex-col gap-1">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold ${accent ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function RunRow({ run }: { run: RunStatus }) {
  const router = useRouter();
  const rec = run.bid_decision?.recommendation;
  return (
    <li
      onClick={() =>
        router.push(
          TERMINAL_STEPS.has(run.current_step)
            ? `/runs/${run.run_id}/result`
            : `/runs/${run.run_id}`
        )
      }
      className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
    >
      <span className="font-mono text-xs text-gray-400 truncate flex-1">
        {run.edital_id.slice(0, 24)}…
      </span>
      <span className={`text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ${stepColor(run.current_step)}`}>
        {STEP_LABEL[run.current_step] ?? run.current_step}
      </span>
      {rec && (
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${REC_COLOR[rec] ?? "bg-gray-100 text-gray-600"}`}>
          {REC_LABEL[rec] ?? rec}
        </span>
      )}
    </li>
  );
}

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
  const participar = decided.filter((r) => r.bid_decision?.recommendation === "participar");
  const participRate =
    decided.length > 0 ? Math.round((participar.length / decided.length) * 100) : null;

  const pendingHITL = hitl?.items.filter((i) => i.status === "pending").length ?? 0;
  const certAlert =
    (certData?.certidoes ?? []).filter(
      (c) => c.status === "expired" || c.status === "expiring_soon"
    ).length;

  const recent = allRuns.slice(0, 6);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Visão geral da sua operação de licitações.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiCard
          label="Análises"
          value={allRuns.length}
          sub="total histórico"
        />
        <KpiCard
          label="Taxa de participação"
          value={participRate !== null ? `${participRate}%` : "—"}
          sub={decided.length > 0 ? `em ${decided.length} análises` : "sem dados"}
          accent={
            participRate !== null && participRate >= 50 ? "text-green-600" : "text-gray-900"
          }
        />
        <KpiCard
          label="Aprovações pendentes"
          value={pendingHITL}
          sub="aguardando revisão humana"
          accent={pendingHITL > 0 ? "text-orange-600" : "text-gray-900"}
        />
        <KpiCard
          label="Certidões em alerta"
          value={certAlert}
          sub="vencidas ou a vencer"
          accent={certAlert > 0 ? "text-red-600" : "text-gray-900"}
        />
      </div>

      {/* Main grid: form + recent runs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Submit form */}
        <div>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Nova análise
          </h2>
          <div className="bg-white rounded-xl border p-6 shadow-sm">
            <SubmitForm />
          </div>
        </div>

        {/* Recent runs */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Análises recentes
            </h2>
            <Link href="/runs" className="text-xs text-blue-600 hover:underline">
              Ver todas →
            </Link>
          </div>
          <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
            {recent.length === 0 ? (
              <p className="text-gray-400 text-sm py-8 text-center">
                Nenhuma análise ainda.
              </p>
            ) : (
              <ul className="divide-y">
                {recent.map((run) => (
                  <RunRow key={run.run_id} run={run} />
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Alerts row */}
      {(pendingHITL > 0 || certAlert > 0) && (
        <div className="flex flex-wrap gap-3">
          {pendingHITL > 0 && (
            <Link
              href="/hitl"
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-orange-50 border border-orange-200 text-orange-700 text-sm font-medium hover:bg-orange-100 transition-colors"
            >
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              {pendingHITL} aprovação{pendingHITL > 1 ? "ões" : ""} pendente{pendingHITL > 1 ? "s" : ""}
            </Link>
          )}
          {certAlert > 0 && (
            <Link
              href="/certidoes"
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-medium hover:bg-red-100 transition-colors"
            >
              <span className="w-2 h-2 rounded-full bg-red-500" />
              {certAlert} certidão{certAlert > 1 ? "ões" : ""} em alerta
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
