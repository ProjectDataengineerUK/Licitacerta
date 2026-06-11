"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Save, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const REGIMES = [
  { value: "simples", label: "Simples Nacional" },
  { value: "lucro_presumido", label: "Lucro Presumido" },
  { value: "lucro_real", label: "Lucro Real" },
];

export default function EmpresaPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["empresa"], queryFn: api.getEmpresa });

  const [form, setForm] = useState({
    name: "", cnpj: "", vertical: "",
    segmentos: "", ufs_interesse: "", regime_tributario: "simples",
  });

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name ?? "",
        cnpj: data.cnpj ?? "",
        vertical: data.vertical ?? "",
        segmentos: data.segmentos?.join(", ") ?? "",
        ufs_interesse: data.ufs_interesse?.join(", ") ?? "",
        regime_tributario: data.regime_tributario ?? "simples",
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () => api.patchEmpresa({
      name: form.name || undefined,
      cnpj: form.cnpj || undefined,
      vertical: form.vertical || undefined,
      segmentos: form.segmentos ? form.segmentos.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
      ufs_interesse: form.ufs_interesse ? form.ufs_interesse.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
      regime_tributario: form.regime_tributario as "simples" | "lucro_presumido" | "lucro_real",
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["empresa"] }),
  });

  const field = (key: keyof typeof form, label: string, placeholder?: string, hint?: string) => (
    <div>
      <label className="block text-xs text-zinc-400 mb-1.5">{label}</label>
      <input
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        placeholder={placeholder}
        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      {hint && <p className="text-[11px] text-zinc-600 mt-1">{hint}</p>}
    </div>
  );

  if (isLoading) return <div className="text-zinc-500 text-sm">Carregando...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <Building2 className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Empresa</h1>
          <p className="text-xs text-zinc-500">Perfil do tenant na plataforma</p>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
        {field("name", "Nome da empresa", "Minha Empresa Ltda")}
        {field("cnpj", "CNPJ", "00.000.000/0001-00")}
        {field("vertical", "Vertical / Setor", "construção, tecnologia, saúde...")}
        {field("segmentos", "Segmentos (separados por vírgula)", "obras, TI, serviços")}
        {field("ufs_interesse", "UFs de interesse (separadas por vírgula)", "SP, RJ, MG")}

        <div>
          <label className="block text-xs text-zinc-400 mb-1.5">Regime tributário</label>
          <select
            value={form.regime_tributario}
            onChange={(e) => setForm({ ...form, regime_tributario: e.target.value })}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {REGIMES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>

        {save.isError && (
          <p className="text-xs text-red-400">
            {save.error instanceof Error ? save.error.message : "Erro ao salvar"}
          </p>
        )}
        {save.isSuccess && <p className="text-xs text-emerald-400">Salvo com sucesso.</p>}

        <button
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-sm font-semibold text-white transition-colors"
        >
          {save.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Salvar
        </button>
      </div>
    </div>
  );
}
