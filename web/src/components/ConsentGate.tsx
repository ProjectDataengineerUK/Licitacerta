"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export function ConsentGate() {
  const qc = useQueryClient();
  const [tou, setTou] = useState(false);
  const [privacy, setPrivacy] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["lgpd", "consent-status"],
    queryFn: () => api.getConsentStatus(),
    staleTime: 5 * 60 * 1000,
  });

  const accept = useMutation({
    mutationFn: () => api.postConsent({ accepted_tou: tou, accepted_privacy: privacy }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lgpd", "consent-status"] });
    },
  });

  const open = !isLoading && data?.needs_consent === true;
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      aria-describedby="consent-desc"
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-6 h-6 text-emerald-400" aria-hidden="true" />
          <h2 id="consent-title" className="text-lg font-semibold text-zinc-100">
            Antes de continuar
          </h2>
        </div>
        <p id="consent-desc" className="text-sm text-zinc-400 mb-5">
          Para usar a LicitaCerta você precisa aceitar nossos Termos de Uso e a Política de
          Privacidade (LGPD). Marque ambos para prosseguir.
        </p>
        <fieldset className="space-y-3 mb-5">
          <legend className="sr-only">Consentimentos obrigatórios</legend>
          <label className="flex items-start gap-3 p-3 rounded-lg border border-zinc-700 hover:border-zinc-600 cursor-pointer">
            <input
              type="checkbox"
              checked={tou}
              onChange={(e) => setTou(e.target.checked)}
              className="mt-0.5 accent-emerald-500"
              aria-describedby="tou-desc"
            />
            <span>
              <span className="block text-sm font-medium text-zinc-200">
                Aceito os{" "}
                <a
                  href="/legal/termos"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 underline"
                >
                  Termos de Uso
                </a>
              </span>
              <span id="tou-desc" className="block text-xs text-zinc-500">
                Condições gerais de uso da plataforma.
              </span>
            </span>
          </label>
          <label className="flex items-start gap-3 p-3 rounded-lg border border-zinc-700 hover:border-zinc-600 cursor-pointer">
            <input
              type="checkbox"
              checked={privacy}
              onChange={(e) => setPrivacy(e.target.checked)}
              className="mt-0.5 accent-emerald-500"
              aria-describedby="privacy-desc"
            />
            <span>
              <span className="block text-sm font-medium text-zinc-200">
                Aceito a{" "}
                <a
                  href="/legal/privacidade"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 underline"
                >
                  Política de Privacidade
                </a>
              </span>
              <span id="privacy-desc" className="block text-xs text-zinc-500">
                Tratamento de dados conforme a LGPD (Lei 13.709/2018).
              </span>
            </span>
          </label>
        </fieldset>
        {accept.isError && (
          <p role="alert" className="text-xs text-red-400 mb-3">
            {accept.error instanceof Error ? accept.error.message : "Erro ao salvar consentimento"}
          </p>
        )}
        <button
          type="button"
          onClick={() => accept.mutate()}
          disabled={!(tou && privacy) || accept.isPending}
          className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold text-white flex items-center justify-center gap-2"
        >
          {accept.isPending && (
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          )}
          Concordar e continuar
        </button>
      </div>
    </div>
  );
}
