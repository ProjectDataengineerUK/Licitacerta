"use client";
import { useState } from "react";
import { api } from "@/lib/api";

const SEGMENTOS = [
  "Tecnologia da Informação",
  "Limpeza e Conservação",
  "Obras e Construção",
  "Saúde",
  "Educação",
  "Alimentação",
  "Segurança",
  "Outros",
];

const UFS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA",
  "MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN",
  "RS","RO","RR","SC","SP","SE","TO",
];

interface Props {
  onBack: () => void;
  onNext: (data: Record<string, unknown>) => void;
}

export function WizardStep2({ onBack, onNext }: Props) {
  const [segmento, setSegmento] = useState("");
  const [ufs, setUfs] = useState<string[]>([]);
  const [salvando, setSalvando] = useState(false);

  function toggleUf(uf: string) {
    setUfs((prev) => prev.includes(uf) ? prev.filter((u) => u !== uf) : [...prev, uf]);
  }

  async function handleNext() {
    setSalvando(true);
    try {
      await api.updateAtivacaoStep(2, { segmento, ufs });
    } catch {
      // non-blocking
    } finally {
      setSalvando(false);
    }
    onNext({ segmento, ufs });
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100 mb-1">Segmento e regiões</h2>
        <p className="text-sm text-zinc-400">Selecione onde sua empresa atua para personalizarmos os alertas.</p>
      </div>
      <div>
        <label className="block text-xs text-zinc-500 mb-1.5">Segmento principal</label>
        <select
          value={segmento}
          onChange={(e) => setSegmento(e.target.value)}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200"
        >
          <option value="">Selecione…</option>
          {SEGMENTOS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-zinc-500 mb-2">UFs de interesse</label>
        <div className="flex flex-wrap gap-1.5">
          {UFS.map((uf) => (
            <button
              key={uf}
              type="button"
              onClick={() => toggleUf(uf)}
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                ufs.includes(uf)
                  ? "bg-emerald-600 border-emerald-500 text-white"
                  : "bg-zinc-800 border-zinc-700 text-zinc-400 hover:border-zinc-500"
              }`}
            >
              {uf}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-2 pt-2">
        <button
          onClick={onBack}
          className="flex-1 border border-zinc-700 text-zinc-400 text-sm py-2.5 rounded-lg hover:border-zinc-500"
        >
          Voltar
        </button>
        <button
          onClick={handleNext}
          disabled={!segmento || salvando}
          className="flex-1 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-40 text-white text-sm font-semibold py-2.5 rounded-lg"
        >
          {salvando ? "Salvando…" : "Continuar"}
        </button>
      </div>
    </div>
  );
}
