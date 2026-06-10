"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Kanban, Wallet, Bell, ShieldCheck, Eye,
  History, FileText, Award, Settings, LogOut, FileSearch,
} from "lucide-react";
import { useHITL } from "@/lib/hooks/useHITL";
import { useAuth } from "@/components/providers";
import { signOutUser } from "@/lib/firebase";

const NAV = [
  {
    section: "Operação",
    items: [
      { href: "/", icon: LayoutDashboard, label: "Cockpit" },
      { href: "/pipeline", icon: Kanban, label: "Pipeline" },
      { href: "/financeiro", icon: Wallet, label: "Financeiro" },
      { href: "/alertas", icon: Bell, label: "Alertas" },
    ],
  },
  {
    section: "Monitoramento",
    items: [
      { href: "/hitl", icon: ShieldCheck, label: "Aprovações", badge: "hitl" as const },
      { href: "/watch", icon: Eye, label: "Watch" },
      { href: "/runs", icon: History, label: "Histórico" },
      { href: "/certidoes", icon: FileText, label: "Certidões" },
      { href: "/contracts", icon: Award, label: "Contratos" },
    ],
  },
  {
    section: "Conta",
    items: [
      { href: "/config/empresa", icon: Settings, label: "Configurações" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: hitlData } = useHITL();
  const { user } = useAuth();
  const hitlCount = hitlData?.items.filter((i) => i.status === "pending").length ?? 0;

  return (
    <aside className="hidden lg:flex w-[220px] shrink-0 flex-col h-screen sticky top-0 border-r border-zinc-800/50 bg-zinc-950">
      {/* Logo */}
      <div className="px-4 py-5 flex items-center gap-2.5 border-b border-zinc-800/50">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-md shadow-blue-500/20 shrink-0">
          <FileSearch className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-zinc-100 text-[15px] tracking-tight">
          Licita<span className="text-blue-400">Certa</span>
        </span>
      </div>

      {/* Nav groups */}
      <nav className="flex-1 px-2 py-4 space-y-5 overflow-y-auto">
        {NAV.map(({ section, items }) => (
          <div key={section}>
            <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-zinc-600 mb-1">
              {section}
            </p>
            <div className="space-y-0.5">
              {items.map(({ href, icon: Icon, label, badge }) => {
                const active = pathname === href;
                const count = badge === "hitl" ? hitlCount : 0;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`group flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150 ${
                      active
                        ? "bg-blue-500/10 text-blue-400 font-medium"
                        : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60"
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 shrink-0 transition-colors ${
                        active ? "text-blue-400" : "text-zinc-600 group-hover:text-zinc-400"
                      }`}
                    />
                    <span className="flex-1">{label}</span>
                    {count > 0 && (
                      <span className="bg-orange-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                        {count}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      {user && (
        <div className="px-3 py-4 border-t border-zinc-800/50">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-semibold text-zinc-300 shrink-0">
              {user.email?.[0]?.toUpperCase() ?? "U"}
            </div>
            <p className="text-xs text-zinc-400 truncate flex-1 min-w-0">{user.email}</p>
            <button
              onClick={signOutUser}
              className="text-zinc-600 hover:text-zinc-400 transition-colors shrink-0"
              title="Sair"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
