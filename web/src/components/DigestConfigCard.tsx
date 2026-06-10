"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const UFS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
  "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
];

interface DigestConfig {
  tenant_id: string;
  ufs: string[];
  cnaes: string[];
  valor_min: number | null;
  valor_max: number | null;
  palavras_chave: string[];
  ativo: boolean;
  canal_email: boolean;
  canal_push: boolean;
}

const EMPTY: DigestConfig = {
  tenant_id: "", ufs: [], cnaes: [], valor_min: null, valor_max: null,
  palavras_chave: [], ativo: true, canal_email: true, canal_push: false,
};

export function DigestConfigCard() {
  const [cfg, setCfg] = useState<DigestConfig>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [cnaeInput, setCnaeInput] = useState("");
  const [palavraInput, setPalavraInput] = useState("");

  useEffect(() => {
    api.getDigestConfig()
      .then((c) => setCfg(c as DigestConfig))
      .catch(() => setCfg(EMPTY))
      .finally(() => setLoading(false));
  }, []);

  function toggleUf(uf: string) {
    setCfg((c) => ({
      ...c,
      ufs: c.ufs.includes(uf) ? c.ufs.filter((u) => u !== uf) : [...c.ufs, uf],
    }));
  }

  function addCnae() {
    const v = cnaeInput.trim();
    if (v && !cfg.cnaes.includes(v)) setCfg((c) => ({ ...c, cnaes: [...c.cnaes, v] }));
    setCnaeInput("");
  }

  function addPalavra() {
    const v = palavraInput.trim();
    if (v && !cfg.palavras_chave.includes(v))
      setCfg((c) => ({ ...c, palavras_chave: [...c.palavras_chave, v] }));
    setPalavraInput("");
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await api.putDigestConfig({
        ufs: cfg.ufs, cnaes: cfg.cnaes, valor_min: cfg.valor_min,
        valor_max: cfg.valor_max, palavras_chave: cfg.palavras_chave,
        ativo: cfg.ativo, canal_email: cfg.canal_email, canal_push: cfg.canal_push,
      });
      setCfg(updated as DigestConfig);
      setSavedAt(new Date().toLocaleTimeString());
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-sm text-gray-400 p-5">Carregando…</div>;

  return (
    <div className="border border-gray-200 rounded-xl p-5 space-y-5 bg-white shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Digest diário de oportunidades</h3>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={cfg.ativo}
            onChange={(e) => setCfg((c) => ({ ...c, ativo: e.target.checked }))} />
          <span className="text-gray-600">Ativo</span>
        </label>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">UFs de interesse</p>
        <div className="flex flex-wrap gap-1.5">
          {UFS.map((uf) => (
            <button key={uf} type="button" onClick={() => toggleUf(uf)}
              className={`text-xs rounded-full px-2.5 py-1 border ${
                cfg.ufs.includes(uf)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
              }`}>
              {uf}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">CNAEs</p>
        <div className="flex gap-2 mb-2">
          <input value={cnaeInput} onChange={(e) => setCnaeInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCnae())}
            placeholder="ex.: 6201-5" className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5" />
          <button type="button" onClick={addCnae}
            className="text-sm bg-gray-100 hover:bg-gray-200 rounded-lg px-3">Adicionar</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {cfg.cnaes.map((c) => (
            <span key={c} className="text-xs bg-blue-50 text-blue-700 rounded-full px-2.5 py-0.5 flex items-center gap-1">
              {c}
              <button onClick={() => setCfg((s) => ({ ...s, cnaes: s.cnaes.filter((x) => x !== c) }))}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Palavras-chave</p>
        <div className="flex gap-2 mb-2">
          <input value={palavraInput} onChange={(e) => setPalavraInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addPalavra())}
            placeholder="ex.: suporte técnico" className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5" />
          <button type="button" onClick={addPalavra}
            className="text-sm bg-gray-100 hover:bg-gray-200 rounded-lg px-3">Adicionar</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {cfg.palavras_chave.map((p) => (
            <span key={p} className="text-xs bg-emerald-50 text-emerald-700 rounded-full px-2.5 py-0.5 flex items-center gap-1">
              {p}
              <button onClick={() => setCfg((s) => ({ ...s, palavras_chave: s.palavras_chave.filter((x) => x !== p) }))}>×</button>
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm">
          <span className="text-gray-500 text-xs block mb-1">Valor mínimo (R$)</span>
          <input type="number" min={0} value={cfg.valor_min ?? ""}
            onChange={(e) => setCfg((c) => ({ ...c, valor_min: e.target.value ? Number(e.target.value) : null }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-1.5" />
        </label>
        <label className="text-sm">
          <span className="text-gray-500 text-xs block mb-1">Valor máximo (R$)</span>
          <input type="number" min={0} value={cfg.valor_max ?? ""}
            onChange={(e) => setCfg((c) => ({ ...c, valor_max: e.target.value ? Number(e.target.value) : null }))}
            className="w-full border border-gray-200 rounded-lg px-3 py-1.5" />
        </label>
      </div>

      <div className="flex gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={cfg.canal_email}
            onChange={(e) => setCfg((c) => ({ ...c, canal_email: e.target.checked }))} />
          E-mail
        </label>
        <label className="flex items-center gap-2 text-gray-400">
          <input type="checkbox" checked={cfg.canal_push} disabled />
          Push (em breve)
        </label>
      </div>

      <div className="flex items-center justify-end gap-3">
        {savedAt && <span className="text-xs text-emerald-600">Salvo às {savedAt}</span>}
        <button onClick={save} disabled={saving}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-5 py-2">
          {saving ? "Salvando…" : "Salvar preferências"}
        </button>
      </div>
    </div>
  );
}
