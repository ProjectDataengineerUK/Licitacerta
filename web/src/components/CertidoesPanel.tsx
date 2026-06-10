"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  valida: { label: "Válida", color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  vence_em_breve: { label: "Vence em breve", color: "text-amber-700 bg-amber-50 border-amber-200" },
  vencida: { label: "Vencida", color: "text-red-700 bg-red-50 border-red-200" },
  nao_verificada: { label: "Não verificada", color: "text-gray-600 bg-gray-50 border-gray-200" },
};

const TIPOS = [
  { value: "CND_FEDERAL", label: "CND Federal" },
  { value: "FGTS", label: "FGTS" },
  { value: "TRABALHISTA", label: "Trabalhista (CNDT)" },
  { value: "ESTADUAL_SEFAZ", label: "Estadual (SEFAZ)" },
  { value: "MUNICIPAL_ISSQN", label: "Municipal (ISSQN)" },
];

interface Certidao {
  id: string;
  tenant_id: string;
  cnpj: string;
  tipo: string;
  validade: string | null;
  status: string;
  url_documento: string | null;
  verificado_em: string | null;
  ultimo_alerta: string | null;
  created_at: string;
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.nao_verificada;
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

export function CertidoesPanel() {
  const [items, setItems] = useState<Certidao[]>([]);
  const [habilitado, setHabilitado] = useState(false);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [cnpj, setCnpj] = useState("");
  const [tipo, setTipo] = useState(TIPOS[0].value);
  const [validade, setValidade] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await api.listCertidoes();
      setItems(res.certidoes);
      setHabilitado(res.alertas_habilitados);
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao carregar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true);
    try {
      await api.createCertidao({ cnpj, tipo, validade: validade || null });
      setCnpj("");
      setValidade("");
      setTipo(TIPOS[0].value);
      await load();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao salvar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Certidões</h2>
        {habilitado ? (
          <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
            Alertas automáticos ativos
          </span>
        ) : (
          <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
            Upgrade p/ alertas automáticos
          </span>
        )}
      </div>

      {!habilitado && (
        <div className="border border-amber-200 bg-amber-50 rounded-xl p-4 text-sm text-amber-800">
          No plano atual você visualiza o status das certidões. Os alertas automáticos (D-30/15/7/1
          e vencidas) estão disponíveis a partir do plano Profissional.
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="border rounded-xl p-4 grid gap-3 sm:grid-cols-4"
      >
        <input
          required
          value={cnpj}
          onChange={(e) => setCnpj(e.target.value)}
          placeholder="CNPJ"
          className="border rounded-lg px-3 py-2 text-sm sm:col-span-1"
        />
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm sm:col-span-1"
        >
          {TIPOS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={validade}
          onChange={(e) => setValidade(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm sm:col-span-1"
        />
        <button
          type="submit"
          disabled={salvando}
          className="bg-gray-900 text-white text-sm font-semibold rounded-lg px-4 py-2 disabled:opacity-50 sm:col-span-1"
        >
          {salvando ? "Salvando…" : "Adicionar"}
        </button>
      </form>

      {erro && <p className="text-sm text-red-700">{erro}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">Nenhuma certidão cadastrada.</p>
      ) : (
        <div className="border rounded-xl divide-y">
          {items.map((c) => (
            <div key={c.id} className="flex items-center justify-between p-4">
              <div>
                <p className="font-medium text-sm">
                  {TIPOS.find((t) => t.value === c.tipo)?.label ?? c.tipo}
                </p>
                <p className="text-xs text-gray-500">
                  CNPJ {c.cnpj}
                  {c.validade
                    ? ` · vence ${new Date(c.validade).toLocaleDateString("pt-BR")}`
                    : " · sem validade"}
                </p>
              </div>
              <StatusBadge status={c.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
