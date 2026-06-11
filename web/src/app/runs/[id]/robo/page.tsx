"use client";

import { useState } from "react";
import { useParams } from "next/navigation";

interface RoboStatus {
  session_id?: string;
  status: string;
  posicao_final?: number;
  valor_final_brl?: number;
  motivo_encerramento?: string;
  lances: Array<{
    numero: number;
    valor_brl: string;
    posicao_resultante?: number;
    motivo: string;
    aprovado_hitl: boolean;
    timestamp_utc: string;
  }>;
  aviso?: string;
}

const BRL = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function RoboPage() {
  const { id: runId } = useParams<{ id: string }>();

  const [floor, setFloor] = useState("");
  const [decremento, setDecremento] = useState("0.5");
  const [posicaoAlvo, setPosicaoAlvo] = useState("1");
  const [margemMinima, setMargemMinima] = useState("5");
  const [estrategia, setEstrategia] = useState("por_posicao");
  const [status, setStatus] = useState<RoboStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [aceiteToS, setAceiteToS] = useState(false);

  const ativar = async () => {
    if (!aceiteToS) {
      setError("Você deve aceitar os Termos de Uso antes de ativar.");
      return;
    }
    if (!floor) {
      setError("Informe o valor mínimo (floor).");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`/api/runs/${runId}/robo/ativar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          estrategia,
          posicao_alvo: parseInt(posicaoAlvo),
          margem_minima_pct: parseFloat(margemMinima),
          valor_floor_brl: parseFloat(floor),
          decremento_pct: parseFloat(decremento),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Erro ao ativar.");
        return;
      }
      setStatus({ status: data.status, lances: [], aviso: data.aviso });
    } catch {
      setError("Erro de conexão.");
    } finally {
      setLoading(false);
    }
  };

  const parar = async () => {
    setLoading(true);
    try {
      await fetch(`/api/runs/${runId}/robo/parar`, { method: "POST" });
      await refreshStatus();
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    try {
      const res = await fetch(`/api/runs/${runId}/robo/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      // silent
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6 px-4">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Robô de Lances</h1>
          <p className="text-sm text-gray-500 mt-1">Automação de lances no pregão eletrônico.</p>
        </div>
        <span className="bg-purple-100 text-purple-700 text-xs font-semibold px-2.5 py-1 rounded-full">
          Business
        </span>
      </div>

      {/* ToS disclaimer */}
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-5 space-y-3">
        <p className="font-semibold text-amber-900 text-sm">Aviso importante</p>
        <p className="text-sm text-amber-800">
          A automação de lances por browser está em revisão de conformidade com os Termos de Uso dos portais de
          compras públicas (ComprasNet, BLL, BNC). Ao ativar, você confirma que tem autorização para operar
          automações no portal e assume responsabilidade pelo uso desta ferramenta.
        </p>
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={aceiteToS}
            onChange={(e) => setAceiteToS(e.target.checked)}
            className="mt-0.5 accent-amber-600"
          />
          <span className="text-xs text-amber-700 font-medium">
            Li, compreendi e aceito os Termos de Uso e as Condições de Automação.
          </span>
        </label>
      </div>

      {/* Config form */}
      {!status && (
        <div className="bg-white border rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-800">Configuração</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Estratégia</label>
              <select
                value={estrategia}
                onChange={(e) => setEstrategia(e.target.value)}
                className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="por_posicao">Por posição</option>
                <option value="por_margem">Por margem mínima</option>
                <option value="por_valor">Por valor fixo</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-gray-500 mb-1 block">Valor mínimo (floor) R$</label>
              <input
                type="number"
                value={floor}
                onChange={(e) => setFloor(e.target.value)}
                className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Ex: 90000"
              />
            </div>

            <div>
              <label className="text-xs text-gray-500 mb-1 block">Decremento (%)</label>
              <input
                type="number"
                step="0.1"
                value={decremento}
                onChange={(e) => setDecremento(e.target.value)}
                className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {estrategia === "por_posicao" && (
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Posição alvo</label>
                <input
                  type="number"
                  value={posicaoAlvo}
                  onChange={(e) => setPosicaoAlvo(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min={1}
                />
              </div>
            )}

            {estrategia === "por_margem" && (
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Margem mínima (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={margemMinima}
                  onChange={(e) => setMargemMinima(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            onClick={ativar}
            disabled={loading || !aceiteToS}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl transition-colors text-sm"
          >
            {loading ? "Ativando…" : "Ativar Robô"}
          </button>
        </div>
      )}

      {/* Status panel */}
      {status && (
        <div className="bg-white border rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-800">Status da sessão</h2>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
              status.status === "em_andamento"
                ? "bg-emerald-100 text-emerald-700"
                : status.status === "encerrada"
                ? "bg-gray-100 text-gray-500"
                : "bg-amber-100 text-amber-700"
            }`}>
              {status.status}
            </span>
          </div>

          {status.aviso && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {status.aviso}
            </p>
          )}

          {status.lances.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-400 uppercase">
                <tr>
                  <th className="text-left py-1">#</th>
                  <th className="text-right py-1">Valor</th>
                  <th className="text-right py-1">Posição</th>
                  <th className="text-right py-1">Motivo</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {status.lances.map((l) => (
                  <tr key={l.numero}>
                    <td className="py-2 text-gray-500">{l.numero}</td>
                    <td className="py-2 text-right font-medium">{BRL(parseFloat(l.valor_brl))}</td>
                    <td className="py-2 text-right">{l.posicao_resultante ?? "—"}</td>
                    <td className="py-2 text-right text-xs text-gray-400">{l.motivo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {status.lances.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">Nenhum lance registrado ainda.</p>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={refreshStatus}
              disabled={loading}
              className="flex-1 border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium py-2.5 rounded-xl text-sm transition-colors"
            >
              Atualizar
            </button>
            <button
              onClick={parar}
              disabled={loading || status.status === "encerrada"}
              className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white font-semibold py-2.5 rounded-xl text-sm transition-colors"
            >
              Parar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
