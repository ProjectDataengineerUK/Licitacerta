"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const TIPOS = [
  { key: "vencimento_certidao", label: "Vencimento de certidão" },
  { key: "prazo_impugnacao",    label: "Prazo de impugnação" },
  { key: "analise_concluida",   label: "Análise concluída" },
  { key: "novo_edital",         label: "Novo edital no Radar" },
  { key: "contrato_vencendo",   label: "Contrato vencendo" },
];

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-6 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-zinc-700"}`}
    >
      <span className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${checked ? "translate-x-5" : "translate-x-1"}`} />
    </button>
  );
}

export default function NotifPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["notif-prefs"], queryFn: api.getNotifPrefs });

  const patch = useMutation({
    mutationFn: (body: Parameters<typeof api.patchNotifPrefs>[0]) => api.patchNotifPrefs(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notif-prefs"] }),
  });

  if (isLoading || !data) return <div className="text-zinc-500 text-sm">Carregando...</div>;

  const toggleTipo = (key: string) => {
    const cur = data.tipos_habilitados ?? [];
    const next = cur.includes(key) ? cur.filter((t) => t !== key) : [...cur, key];
    patch.mutate({ tipos_habilitados: next });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <Bell className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Notificações</h1>
          <p className="text-xs text-zinc-500">Canais e tipos de alerta habilitados</p>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-5">
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">Canais</p>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-zinc-200">E-mail</p>
            <p className="text-xs text-zinc-500">Recebe alertas por e-mail</p>
          </div>
          {patch.isPending ? <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" /> : (
            <Toggle checked={data.email_enabled} onChange={(v) => patch.mutate({ email_enabled: v })} />
          )}
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-zinc-200">WhatsApp</p>
            <p className="text-xs text-zinc-500">Integração via número cadastrado</p>
          </div>
          {patch.isPending ? <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" /> : (
            <Toggle checked={data.whatsapp_enabled} onChange={(v) => patch.mutate({ whatsapp_enabled: v })} />
          )}
        </div>

        {data.whatsapp_enabled && (
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Número WhatsApp</label>
            <input
              defaultValue={data.whatsapp_number ?? ""}
              onBlur={(e) => patch.mutate({ whatsapp_number: e.target.value || null })}
              placeholder="+55 11 99999-9999"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        )}

        <div className="border-t border-zinc-800 pt-4">
          <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-3">Tipos de alerta</p>
          <ul className="space-y-3">
            {TIPOS.map(({ key, label }) => {
              const enabled = data.tipos_habilitados?.includes(key) ?? false;
              return (
                <li key={key} className="flex items-center justify-between">
                  <p className="text-sm text-zinc-300">{label}</p>
                  <Toggle checked={enabled} onChange={() => toggleTipo(key)} />
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
