"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

interface SimulacaoAntecipacao {
  valor_bruto_brl: number;
  prazo_dias: number;
  taxa_mensal_pct: number;
  taxa_periodo: number;
  custo_antecipacao_brl: number;
  valor_liquido_brl: number;
  custo_efetivo_anual_pct: number;
  elegivel: boolean;
  motivo_inelegivel?: string;
}

const BRL = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function RecebiveisContent() {
  const searchParams = useSearchParams();
  const runIdParam = searchParams.get("run_id") || "";
  const valorParam = searchParams.get("valor_bruto") || "";

  const [valorBruto, setValorBruto] = useState(valorParam);
  const [prazoDias, setPrazoDias] = useState("60");
  const [runId, setRunId] = useState(runIdParam);
  const [simulacao, setSimulacao] = useState<SimulacaoAntecipacao | null>(null);
  const [loading, setLoading] = useState(false);
  const [solicitando, setSolicitando] = useState(false);
  const [aceite, setAceite] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");

  const simular = async () => {
    if (!valorBruto || !prazoDias) {
      setError("Preencha valor e prazo.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/recebiveis/simular", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          valor_bruto_brl: parseFloat(valorBruto),
          prazo_dias: parseInt(prazoDias),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
        setError(err.detail || `Erro ${res.status}`);
        return;
      }
      setSimulacao(await res.json());
    } catch {
      setError("Erro de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const solicitar = async () => {
    if (!aceite) {
      setError("Você precisa aceitar os termos.");
      return;
    }
    setSolicitando(true);
    setError("");
    try {
      const res = await fetch("/api/recebiveis/solicitar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: runId || "00000000-0000-0000-0000-000000000000",
          valor_bruto_brl: parseFloat(valorBruto),
          prazo_dias: parseInt(prazoDias),
          aceite_termos: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Erro ao solicitar.");
        return;
      }
      setToast(data.mensagem || "Solicitação registrada com sucesso!");
      setSimulacao(null);
    } catch {
      setError("Erro ao registrar solicitação.");
    } finally {
      setSolicitando(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6 px-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Antecipação de Recebíveis</h1>
          <p className="text-sm text-gray-500 mt-1">Receba agora, pague com o contrato.</p>
        </div>
        <span className="bg-purple-100 text-purple-700 text-xs font-semibold px-2.5 py-1 rounded-full">
          Business
        </span>
      </div>

      {toast && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-4 text-sm text-green-800 flex items-start gap-2">
          <span>✓</span>
          <p>{toast}</p>
        </div>
      )}

      {/* Simulator form */}
      <div className="bg-white border rounded-xl p-6 space-y-4">
        <h2 className="font-semibold text-gray-800">Simular antecipação</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Valor bruto (R$)</label>
            <input
              type="number"
              value={valorBruto}
              onChange={(e) => setValorBruto(e.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ex: 50000"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Prazo (dias)</label>
            <input
              type="number"
              value={prazoDias}
              onChange={(e) => setPrazoDias(e.target.value)}
              className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ex: 60"
            />
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
        )}

        <button
          onClick={simular}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm"
        >
          {loading ? "Simulando…" : "Simular"}
        </button>
      </div>

      {/* Result */}
      {simulacao && !simulacao.elegivel && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <p className="font-semibold text-amber-800 mb-1">Não elegível</p>
          <p className="text-sm text-amber-700">{simulacao.motivo_inelegivel}</p>
        </div>
      )}

      {simulacao && simulacao.elegivel && (
        <div className="bg-white border rounded-xl p-6 space-y-5">
          <h2 className="font-semibold text-gray-800">Resultado da simulação</h2>

          <table className="w-full text-sm">
            <tbody className="divide-y">
              <tr className="py-2">
                <td className="py-2.5 text-gray-500">Valor bruto</td>
                <td className="py-2.5 text-right font-medium">{BRL(simulacao.valor_bruto_brl)}</td>
              </tr>
              <tr>
                <td className="py-2.5 text-gray-500">Taxa mensal</td>
                <td className="py-2.5 text-right font-medium">{simulacao.taxa_mensal_pct.toFixed(2)}%</td>
              </tr>
              <tr>
                <td className="py-2.5 text-gray-500">Custo da antecipação</td>
                <td className="py-2.5 text-right text-red-600 font-medium">
                  - {BRL(simulacao.custo_antecipacao_brl)}
                </td>
              </tr>
              <tr className="font-semibold text-base">
                <td className="py-3 text-gray-800">Valor líquido a receber</td>
                <td className="py-3 text-right text-green-700">{BRL(simulacao.valor_liquido_brl)}</td>
              </tr>
              <tr>
                <td className="py-2.5 text-gray-400 text-xs">Custo efetivo anual</td>
                <td className="py-2.5 text-right text-xs text-gray-400">
                  {simulacao.custo_efetivo_anual_pct.toFixed(1)}% a.a.
                </td>
              </tr>
            </tbody>
          </table>

          <div className="border-t pt-4 space-y-3">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={aceite}
                onChange={(e) => setAceite(e.target.checked)}
                className="mt-0.5 accent-blue-600"
              />
              <span className="text-xs text-gray-600">
                Declaro que li e aceito os{" "}
                <span className="text-blue-600 underline cursor-pointer">termos e condições</span>{" "}
                da antecipação de recebíveis e estou ciente de que esta simulação não constitui oferta firme.
              </span>
            </label>

            <button
              onClick={solicitar}
              disabled={solicitando || !aceite}
              className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm"
            >
              {solicitando ? "Registrando…" : "Solicitar antecipação"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RecebiveisPage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-gray-400 text-sm">Carregando…</div>}>
      <RecebiveisContent />
    </Suspense>
  );
}
