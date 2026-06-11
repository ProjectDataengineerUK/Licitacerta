"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, UserPlus, Trash2, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { RoleBadge } from "@/components/RoleBadge";
import { InviteModal } from "@/components/InviteModal";
import type { UserRole } from "@/lib/types";

export default function UsuariosPage() {
  const qc = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: ["usuarios"], queryFn: api.listUsuarios, refetchInterval: 30_000 });

  const revoke = useMutation({
    mutationFn: (id: string) => api.revogarMembro(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
  });

  const changePapel = useMutation({
    mutationFn: ({ id, papel }: { id: string; papel: string }) => api.alterarPapel(id, papel),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
  });

  if (isLoading) return <div className="text-zinc-500 text-sm">Carregando...</div>;

  const members = data?.members ?? [];
  const invites = data?.invites ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
            <Users className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Usuários</h1>
            <p className="text-xs text-zinc-500">Membros e convites pendentes</p>
          </div>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-semibold text-white transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Convidar
        </button>
      </div>

      {/* Membros */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
        <div className="px-5 py-3 border-b border-zinc-800">
          <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Membros ativos</p>
        </div>
        {members.length === 0 ? (
          <p className="text-sm text-zinc-600 text-center py-8">Nenhum membro cadastrado.</p>
        ) : (
          <ul className="divide-y divide-zinc-800">
            {members.map((m) => (
              <li key={m.id} className="flex items-center gap-4 px-5 py-3">
                <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-sm font-bold text-zinc-300">
                  {(m.nome ?? m.email)[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-100 truncate">{m.nome ?? m.email}</p>
                  <p className="text-xs text-zinc-500 truncate">{m.email}</p>
                </div>
                <select
                  value={m.papel}
                  onChange={(e) => changePapel.mutate({ id: m.id, papel: e.target.value })}
                  className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {(["admin", "analista", "visualizador"] as UserRole[]).map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <RoleBadge papel={m.papel as UserRole} />
                <button
                  onClick={() => revoke.mutate(m.id)}
                  disabled={revoke.isPending}
                  aria-label="Revogar acesso"
                  className="text-zinc-600 hover:text-red-400 transition-colors disabled:opacity-40"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Convites pendentes */}
      {invites.length > 0 && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <div className="px-5 py-3 border-b border-zinc-800">
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Convites pendentes</p>
          </div>
          <ul className="divide-y divide-zinc-800">
            {invites.map((inv) => (
              <li key={inv.id} className="flex items-center gap-4 px-5 py-3">
                <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 truncate">{inv.email}</p>
                  <p className="text-xs text-zinc-500">
                    Expira em {new Date(inv.expires_at).toLocaleDateString("pt-BR")}
                  </p>
                </div>
                <RoleBadge papel={inv.papel as UserRole} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {showInvite && <InviteModal onClose={() => setShowInvite(false)} />}
    </div>
  );
}
