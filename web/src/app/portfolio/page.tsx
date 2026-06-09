"use client";

import { useState } from "react";

interface Oportunidade {
  run_id: string;
  titulo?: string;
  orgao?: string;
  valor_estimado_brl: number;
  bid_no_bid_score: number;
  probabilidade_vitoria_pct: number;
  custo_estimado_brl: number;
  prazo_pagamento_dias: number;
  data_sessao?: string;
  capacidade_necessaria_pct: number;
}

interface ResultadoCenario {
  nome: "Conservador" | "Moderado" | "Agressivo";
  oportunidades_selecionadas: string[];
  valor_total_brl: number;
  custo_total_brl: number;
  valor_esperado_ponderado_brl: number;
  probabilidade_vitoria_media_pct: number;
  capacidade_utilizada_pct: number;
  roi_esperado_pct: number;
}

interface PortfolioResult {
  conservador: ResultadoCenario;
  moderado: ResultadoCenario;
  agressivo: ResultadoCenario;
  oportunidades_rejeitadas: string[];
  resumo: string;
}

const BRL = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const SCENARIO_COLOR = {
  Conservador: "bg-blue-50 border-blue-200 text-blue-800",
  Moderado:    "bg-amber-50 border-amber-200 text-amber-800",
  Agressivo:   "bg-red-50 border-red-200 text-red-800",
};

function ScenarioPanel({ cenario, ops }: { cenario: ResultadoCenario; ops: Oportunidade[] }) {
  const selectedOps = ops.filter((o) => cenario.oportunidades_selecionadas.includes(o.run_id));
  const colorClass = SCENARIO_COLOR[cenario.nome];

  const exportCsv = () => {
    const header = "run_id,titulo,orgao,valor_estimado,custo_estimado,probabilidade_pct\n";
    const rows = selectedOps.map((o) =>
      `${o.run_id},"${o.titulo || ""}","${o.orgao || ""}",${o.valor_estimado_brl},${o.custo_estimado_brl},${o.probabilidade_vitoria_pct}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `portfolio-${cenario.nome.toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`border rounded-xl p-5 space-y-4 ${colorClass}`}>
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-lg">{cenario.nome}</h3>
        <button
          onClick={exportCsv}
          disabled={selectedOps.length === 0}
          className="text-xs border px-3 py-1.5 rounded-lg hover:bg-white/50 disabled:opacity-40 transition-colors"
        >
          Exportar CSV
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Valor esperado</p>
          <p className="font-bold text-sm">{BRL(cenario.valor_esperado_ponderado_brl)}</p>
        </div>
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">ROI esperado</p>
          <p className="font-bold text-sm">{cenario.roi_esperado_pct.toFixed(0)}%</p>
        </div>
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Prob. média</p>
          <p className="font-bold text-sm">{cenario.probabilidade_vitoria_media_pct.toFixed(0)}%</p>
        </div>
        <div className="bg-white/60 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-500">Capacidade</p>
          <p className="font-bold text-sm">{cenario.capacidade_utilizada_pct.toFixed(0)}%</p>
        </div>
      </div>

      {/* Table */}
      {selectedOps.length === 0 ? (
        <p className="text-sm italic text-gray-500 text-center py-4">Nenhuma oportunidade selecionada neste cenário.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 font-medium">Licitação</th>
              <th className="text-right py-2 font-medium">Valor est.</th>
              <th className="text-right py-2 font-medium">Custo</th>
              <th className="text-right py-2 font-medium">Prob.</th>
              <th className="text-right py-2 font-medium">Cap.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/50">
            {selectedOps.map((o) => (
              <tr key={o.run_id}>
                <td className="py-2 pr-2 truncate max-w-[160px]">{o.titulo || o.run_id.slice(0, 8)}</td>
                <td className="py-2 text-right">{BRL(o.valor_estimado_brl)}</td>
                <td className="py-2 text-right">{BRL(o.custo_estimado_brl)}</td>
                <td className="py-2 text-right">{o.probabilidade_vitoria_pct.toFixed(0)}%</td>
                <td className="py-2 text-right">{o.capacidade_necessaria_pct.toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function PortfolioPage() {
  const [ops, setOps] = useState<Oportunidade[]>([]);
  const [capital, setCapital] = useState("");
  const [capMax, setCapMax] = useState("100");
  const [capAtual, setCapAtual] = useState("0");
  const [result, setResult] = useState<PortfolioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"Conservador" | "Moderado" | "Agressivo">("Moderado");

  const addOp = () => {
    setOps((prev) => [
      ...prev,
      {
        run_id: crypto.randomUUID(),
        titulo: "",
        orgao: "",
        valor_estimado_brl: 0,
        bid_no_bid_score: 0.5,
        probabilidade_vitoria_pct: 50,
        custo_estimado_brl: 0,
        prazo_pagamento_dias: 30,
        capacidade_necessaria_pct: 10,
      },
    ]);
  };

  const updateOp = (idx: number, field: keyof Oportunidade, value: string | number) => {
    setOps((prev) => prev.map((o, i) => (i === idx ? { ...o, [field]: value } : o)));
  };

  const removeOp = (idx: number) => setOps((prev) => prev.filter((_, i) => i !== idx));

  const otimizar = async () => {
    if (ops.length === 0 || !capital) {
      setError("Adicione ao menos uma oportunidade e informe o capital disponível.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/portfolio/otimizar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          oportunidades: ops,
          capital_giro_disponivel_brl: parseFloat(capital),
          capacidade_maxima_pct: parseFloat(capMax) || 100,
          capacidade_atual_pct: parseFloat(capAtual) || 0,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
        setError(err.detail || `Erro ${res.status}`);
        return;
      }
      setResult(await res.json());
      setActiveTab("Moderado");
    } catch (e) {
      setError("Erro de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const cenarioAtivo = result
    ? activeTab === "Conservador"
      ? result.conservador
      : activeTab === "Moderado"
      ? result.moderado
      : result.agressivo
    : null;

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-6 px-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Simulador de Portfólio</h1>
        <p className="text-sm text-gray-500 mt-1">Otimize quais licitações disputar dado seu capital e capacidade.</p>
      </div>

      {/* Inputs globais */}
      <div className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Parâmetros</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Capital de giro disponível (R$)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ex: 200000"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Capacidade máxima (%)</label>
            <input
              type="number"
              value={capMax}
              onChange={(e) => setCapMax(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Capacidade já comprometida (%)</label>
            <input
              type="number"
              value={capAtual}
              onChange={(e) => setCapAtual(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Oportunidades */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Oportunidades ({ops.length})</h2>
          <button
            onClick={addOp}
            className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Adicionar
          </button>
        </div>
        {ops.length === 0 && (
          <p className="text-sm text-gray-400 italic text-center py-6">Nenhuma oportunidade adicionada.</p>
        )}
        {ops.map((op, i) => (
          <div key={op.run_id} className="border rounded-lg p-4 space-y-3 bg-gray-50">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="col-span-2 sm:col-span-2">
                <label className="text-xs text-gray-500 block mb-1">Título</label>
                <input
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  value={op.titulo || ""}
                  onChange={(e) => updateOp(i, "titulo", e.target.value)}
                  placeholder="Ex: Fornec. de material hospitalar"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Valor est. (R$)</label>
                <input
                  type="number"
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  value={op.valor_estimado_brl}
                  onChange={(e) => updateOp(i, "valor_estimado_brl", parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Custo est. (R$)</label>
                <input
                  type="number"
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  value={op.custo_estimado_brl}
                  onChange={(e) => updateOp(i, "custo_estimado_brl", parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Prob. vitória (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  value={op.probabilidade_vitoria_pct}
                  onChange={(e) => {
                    const v = Math.min(100, Math.max(0, parseFloat(e.target.value) || 0));
                    updateOp(i, "probabilidade_vitoria_pct", v);
                    updateOp(i, "bid_no_bid_score", v / 100);
                  }}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Capacidade (%)</label>
                <input
                  type="number"
                  className="w-full border rounded px-2 py-1.5 text-sm"
                  value={op.capacidade_necessaria_pct}
                  onChange={(e) => updateOp(i, "capacidade_necessaria_pct", parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
            <button
              onClick={() => removeOp(i)}
              className="text-xs text-red-500 hover:underline"
            >
              Remover
            </button>
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        onClick={otimizar}
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-semibold py-3 rounded-xl transition-colors"
      >
        {loading ? "Otimizando…" : "Otimizar portfólio"}
      </button>

      {result && (
        <div className="space-y-4">
          <p className="text-sm text-gray-500 italic">{result.resumo}</p>

          {/* Tabs */}
          <div className="flex gap-2">
            {(["Conservador", "Moderado", "Agressivo"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {cenarioAtivo && <ScenarioPanel cenario={cenarioAtivo} ops={ops} />}

          {result.oportunidades_rejeitadas.length > 0 && (
            <div className="text-xs text-gray-400 text-center">
              {result.oportunidades_rejeitadas.length} oportunidade(s) fora de todos os cenários.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
