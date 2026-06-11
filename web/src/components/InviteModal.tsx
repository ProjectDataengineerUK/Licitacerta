"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, UserPlus, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { UserRole } from "@/lib/types";

const ROLES: { value: UserRole; label: string; desc: string }[] = [
  { value: "admin",        label: "Admin",       desc: "Acesso total, pode convidar membros" },
  { value: "analista",     label: "Analista",    desc: "Pode enviar editais e ver resultados" },
  { value: "visualizador", label: "Visualizador",desc: "Apenas leitura" },
];

interface Props {
  onClose: () => void;
}

export function InviteModal({ onClose }: Props) {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [papel, setPapel] = useState<UserRole>("analista");

  const invite = useMutation({
    mutationFn: () => api.convidarUsuario({ email, papel }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["usuarios"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-blue-400" />
            <h2 className="text-base font-semibold text-zinc-100">Convidar membro</h2>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">E-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="email@empresa.com.br"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Papel</label>
            <div className="space-y-2">
              {ROLES.map((r) => (
                <label key={r.value} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                  papel === r.value
                    ? "border-blue-500/50 bg-blue-500/10"
                    : "border-zinc-700 hover:border-zinc-600"
                }`}>
                  <input
                    type="radio"
                    name="papel"
                    value={r.value}
                    checked={papel === r.value}
                    onChange={() => setPapel(r.value)}
                    className="mt-0.5 accent-blue-500"
                  />
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{r.label}</p>
                    <p className="text-xs text-zinc-500">{r.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {invite.isError && (
            <p className="text-xs text-red-400">
              {invite.error instanceof Error ? invite.error.message : "Erro ao enviar convite"}
            </p>
          )}

          <button
            onClick={() => invite.mutate()}
            disabled={!email || invite.isPending}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-sm font-semibold text-white transition-colors flex items-center justify-center gap-2"
          >
            {invite.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Enviar convite
          </button>
        </div>
      </div>
    </div>
  );
}
