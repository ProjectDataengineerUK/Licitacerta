"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Certidao } from "@/lib/types";

const TIPOS = [
  "CND Federal",
  "FGTS",
  "Trabalhista",
  "Estadual",
  "Municipal",
  "Falência/Concordata",
  "Balanço Patrimonial",
  "Atestado Técnico",
  "Contrato Social",
  "Outro",
];

function statusLabel(status: Certidao["status"]) {
  switch (status) {
    case "valid":          return { label: "Válida",           cls: "bg-green-100 text-green-700" };
    case "expiring_soon":  return { label: "Vencendo em breve", cls: "bg-yellow-100 text-yellow-700" };
    case "expired":        return { label: "Vencida",           cls: "bg-red-100 text-red-700" };
    case "pending_review": return { label: "Aguardando revisão", cls: "bg-gray-100 text-gray-600" };
  }
}

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
}

export default function CertidoesPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [tipo, setTipo] = useState(TIPOS[0]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["certidoes"],
    queryFn: () => api.listCertidoes(),
    refetchInterval: 60_000,
  });

  const certidoes = data?.certidoes ?? [];
  const expired = certidoes.filter((c) => c.status === "expired").length;
  const expiringSoon = certidoes.filter((c) => c.status === "expiring_soon").length;

  const upload = useMutation({
    mutationFn: async () => {
      const file = fileRef.current?.files?.[0];
      if (!file) throw new Error("Selecione um arquivo");
      setUploadError("");
      setUploading(true);
      try {
        return await api.uploadCertidao(file, tipo);
      } finally {
        setUploading(false);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["certidoes"] });
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: (e: Error) => setUploadError(e.message),
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Certidões</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Pasta documental da empresa. Certidões vencidas bloqueiam participação.
        </p>
      </div>

      {(expired > 0 || expiringSoon > 0) && (
        <div className="mb-4 p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          {expired > 0 && <span className="font-medium">{expired} vencida{expired > 1 ? "s" : ""}</span>}
          {expired > 0 && expiringSoon > 0 && " · "}
          {expiringSoon > 0 && <span>{expiringSoon} vencendo em breve</span>}
          {" "} — renove antes de submeter uma proposta.
        </div>
      )}

      <div className="bg-white rounded-xl border p-6 shadow-sm mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">Adicionar certidão</h2>
        <div className="flex flex-col sm:flex-row gap-3 items-start">
          <select
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {TIPOS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
          />
          <button
            onClick={() => upload.mutate()}
            disabled={uploading}
            className="text-sm bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-40 transition-colors whitespace-nowrap"
          >
            {uploading ? "Enviando…" : "Enviar"}
          </button>
        </div>
        {uploadError && <p className="text-red-500 text-xs mt-2">{uploadError}</p>}
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Documentos</h2>
          <span className="text-xs text-gray-400">{certidoes.length} item{certidoes.length !== 1 ? "s" : ""}</span>
        </div>
        {isLoading ? (
          <p className="text-gray-500 text-sm py-8 text-center">Carregando…</p>
        ) : !certidoes.length ? (
          <p className="text-gray-400 text-sm py-8 text-center">Nenhuma certidão cadastrada.</p>
        ) : (
          <ul className="divide-y">
            {certidoes.map((cert: Certidao) => {
              const { label, cls } = statusLabel(cert.status);
              const days = daysUntil(cert.valid_until);
              return (
                <li key={cert.id} className="px-6 py-4 flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{cert.tipo}</p>
                    {cert.valid_until && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        Validade: {new Date(cert.valid_until).toLocaleDateString("pt-BR")}
                        {days !== null && days >= 0 && (
                          <span className="ml-1">({days} dia{days !== 1 ? "s" : ""})</span>
                        )}
                      </p>
                    )}
                    <p className="text-xs text-gray-400">
                      Adicionada em {new Date(cert.created_at).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full flex-shrink-0 ${cls}`}>
                    {label}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
