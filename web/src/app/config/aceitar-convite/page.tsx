"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/providers";

export default function AcceptInvitePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const token = searchParams.get("token") ?? "";
  const [autoTriggered, setAutoTriggered] = useState(false);

  const accept = useMutation({
    mutationFn: () => api.aceitarConvite(token, user?.uid ?? token.slice(0, 16)),
    onSuccess: () => {
      setTimeout(() => router.push("/"), 2000);
    },
  });

  useEffect(() => {
    if (token && !autoTriggered) {
      setAutoTriggered(true);
      accept.mutate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 w-full max-w-sm text-center space-y-4">
        {accept.isPending && (
          <>
            <Loader2 className="w-10 h-10 text-blue-400 animate-spin mx-auto" />
            <p className="text-sm text-zinc-300">Validando convite...</p>
          </>
        )}
        {accept.isSuccess && (
          <>
            <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
            <p className="text-base font-semibold text-zinc-100">Convite aceito!</p>
            <p className="text-xs text-zinc-500">Redirecionando para o painel...</p>
          </>
        )}
        {accept.isError && (
          <>
            <XCircle className="w-10 h-10 text-red-400 mx-auto" />
            <p className="text-base font-semibold text-zinc-100">Link inválido ou expirado</p>
            <p className="text-xs text-zinc-500">
              {accept.error instanceof Error ? accept.error.message : "Tente solicitar um novo convite."}
            </p>
            <button onClick={() => router.push("/")} className="text-sm text-blue-400 hover:underline">
              Voltar ao início
            </button>
          </>
        )}
        {!token && (
          <>
            <XCircle className="w-10 h-10 text-red-400 mx-auto" />
            <p className="text-sm text-zinc-400">Token de convite não encontrado na URL.</p>
          </>
        )}
      </div>
    </div>
  );
}
