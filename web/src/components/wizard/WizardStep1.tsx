"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  onNext: (data: Record<string, unknown>) => void;
}

export function WizardStep1({ onNext }: Props) {
  const [cnpj, setCnpj] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [lookup, setLookup] = useState<Record<string, unknown> | null>(null);

  async function handleLookup() {
    setLoading(true);
    setErro(null);
    try {
      const res = await api.cnpjLookup(cnpj);
      setLookup(res);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao consultar CNPJ");
    } finally {
      setLoading(false);
    }
  }

  function handleNext() {
    onNext({ cnpj, ...lookup });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100 mb-1">Dados da sua empresa</h2>
        <p className="text-sm text-zinc-400">Informe o CNPJ para buscarmos os dados automaticamente.</p>
      </div>
      <div className="flex gap-2">
        <input
          value={cnpj}
          onChange={(e) => setCnpj(e.target.value)}
          placeholder="00.000.000/0000-00"
          className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-500"
        />
        <button
          onClick={handleLookup}
          disabled={loading || cnpj.length < 14}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm px-4 py-2 rounded-lg flex items-center gap-1"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          Buscar
        </button>
      </div>
      {erro && <p className="text-xs text-red-400">{erro}</p>}
      {lookup && (
        <div className="bg-zinc-800 rounded-xl p-4 space-y-1.5 text-sm">
          {lookup.razao_social && (
            <p className="text-zinc-100 font-medium">{String(lookup.razao_social)}</p>
          )}
          {lookup.cnae_principal && (
            <p className="text-zinc-400">CNAE: {String(lookup.cnae_principal)}</p>
          )}
          {lookup.municipio && (
            <p className="text-zinc-400">Município: {String(lookup.municipio)}</p>
          )}
          {lookup.source === "fallback" && (
            <p className="text-xs text-amber-400">Dados não encontrados — preencha manualmente se necessário.</p>
          )}
        </div>
      )}
      <button
        onClick={handleNext}
        disabled={!cnpj}
        className="w-full bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 text-white text-sm font-semibold py-2.5 rounded-lg"
      >
        Continuar
      </button>
    </div>
  );
}
