"use client";

import { useQuery } from "@tanstack/react-query";
import { CreditCard, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";

export default function PlanoPage() {
  const { data: usage } = useQuery({ queryKey: ["billing-usage"], queryFn: () => api.getBillingUsage() });
  const { data: plans } = useQuery({ queryKey: ["billing-plans"], queryFn: () => api.listPlans() });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <CreditCard className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Plano</h1>
          <p className="text-xs text-zinc-500">Assinatura e uso atual</p>
        </div>
      </div>

      {usage && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-zinc-100 capitalize">{usage.plan}</p>
            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
              usage.subscription_status === "active"
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                : "bg-amber-500/10 text-amber-300 border-amber-500/30"
            }`}>
              {usage.subscription_status}
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs text-zinc-400 mb-1.5">
              <span>Análises este mês</span>
              <span>{usage.usado} / {usage.limite ?? "∞"}</span>
            </div>
            {usage.limite && (
              <div className="w-full bg-zinc-800 rounded-full h-1.5">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${Math.min(100, (usage.usado / usage.limite) * 100)}%` }}
                />
              </div>
            )}
            {usage.reset_em && (
              <p className="text-[11px] text-zinc-600 mt-1">
                Renova em {new Date(usage.reset_em).toLocaleDateString("pt-BR")}
              </p>
            )}
          </div>

          <a
            href="https://billing.stripe.com/p/login"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors font-medium"
          >
            <ExternalLink className="w-4 h-4" />
            Gerenciar assinatura no Stripe
          </a>
        </div>
      )}

      {plans && plans.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
          <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-4">Planos disponíveis</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {plans.map((p: { nome: string; preco_mensal_brl: number; quota_analises_mes: number | null; feature_proposta: boolean }) => (
              <div key={p.nome} className="border border-zinc-700 rounded-xl p-4">
                <p className="text-sm font-semibold text-zinc-200 capitalize mb-1">{p.nome}</p>
                <p className="text-lg font-bold text-zinc-100">
                  {p.preco_mensal_brl === 0 ? "Grátis" : `R$ ${p.preco_mensal_brl.toFixed(0)}/mês`}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {p.quota_analises_mes ?? "Ilimitadas"} análises/mês
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
