"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileSearch,
  History,
  ShieldCheck,
  Eye,
  Award,
  FileText,
  LogOut,
  Kanban,
  Wallet,
  Bell,
} from "lucide-react";
import { useHITL } from "@/lib/hooks/useHITL";
import { useAuth } from "@/components/providers";
import { signOutUser } from "@/lib/firebase";

const LINKS = [
  { href: "/",           label: "Cockpit",    icon: LayoutDashboard },
  { href: "/pipeline",   label: "Pipeline",   icon: Kanban },
  { href: "/financeiro", label: "Financeiro", icon: Wallet },
  { href: "/alertas",    label: "Alertas",    icon: Bell },
  { href: "/runs",       label: "Histórico",  icon: History },
  { href: "/hitl",       label: "Aprovações", icon: ShieldCheck, badge: true },
  { href: "/watch",      label: "Watch",       icon: Eye },
  { href: "/certidoes",  label: "Certidões",  icon: FileText },
  { href: "/contracts",  label: "Contratos",  icon: Award },
];

export function NavBar() {
  const pathname = usePathname();
  const { data } = useHITL();
  const { user } = useAuth();
  const pendingCount = data?.items.filter((i) => i.status === "pending").length ?? 0;

  return (
    <header className="bg-zinc-900 border-b border-zinc-800 sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-14">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-8">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <FileSearch className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-zinc-100 text-base tracking-tight">
            Licita<span className="text-blue-400">Certa</span>
          </span>
        </div>

        {/* Links */}
        <nav className="flex items-center gap-1 flex-1">
          {LINKS.map(({ href, label, icon: Icon, badge }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span className="hidden sm:inline">{label}</span>
                {badge && pendingCount > 0 && (
                  <span className="ml-0.5 bg-orange-500 text-white text-xs font-bold rounded-full px-1.5 py-0.5 leading-none min-w-[18px] text-center">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        {user && (
          <button
            onClick={signOutUser}
            className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-200 transition-colors ml-4"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Sair</span>
          </button>
        )}
      </div>
    </header>
  );
}
