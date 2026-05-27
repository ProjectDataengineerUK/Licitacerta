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
} from "lucide-react";
import { useHITL } from "@/lib/hooks/useHITL";
import { useAuth } from "@/components/providers";
import { signOutUser } from "@/lib/firebase";

const LINKS = [
  { href: "/",           label: "Dashboard",   icon: LayoutDashboard },
  { href: "/runs",       label: "Histórico",   icon: History },
  { href: "/hitl",       label: "Aprovações",  icon: ShieldCheck, badge: true },
  { href: "/watch",      label: "Watch",        icon: Eye },
  { href: "/certidoes",  label: "Certidões",   icon: FileText },
  { href: "/contracts",  label: "Contratos",   icon: Award },
];

export function NavBar() {
  const pathname = usePathname();
  const { data } = useHITL();
  const { user } = useAuth();
  const pendingCount = data?.items.filter((i) => i.status === "pending").length ?? 0;

  return (
    <header className="bg-white border-b sticky top-0 z-20 shadow-sm">
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-14">
        {/* Logo */}
        <div className="flex items-center gap-2 mr-8">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <FileSearch className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-gray-900 text-base tracking-tight">
            Licita<span className="text-blue-600">Certa</span>
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
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
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
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-700 transition-colors ml-4"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Sair</span>
          </button>
        )}
      </div>
    </header>
  );
}
