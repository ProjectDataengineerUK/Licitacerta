"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function SubmitForm() {
  const router = useRouter();
  const [editalRaw, setEditalRaw] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editalRaw.trim() || !cnpj.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const { run_id } = await api.analyze(editalRaw, cnpj);
      router.push(`/runs/${run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar edital");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          CNPJ da empresa
        </label>
        <input
          type="text"
          value={cnpj}
          onChange={(e) => setCnpj(e.target.value)}
          placeholder="00.000.000/0000-00"
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Texto do edital
        </label>
        <textarea
          value={editalRaw}
          onChange={(e) => setEditalRaw(e.target.value)}
          placeholder="Cole aqui o conteúdo do edital..."
          className="w-full border rounded-lg px-3 py-2 text-sm h-64 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
          required
        />
      </div>

      {error && (
        <p className="text-red-500 text-sm bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading || !editalRaw.trim() || !cnpj.trim()}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Enviando..." : "Analisar Edital"}
      </button>
    </form>
  );
}
