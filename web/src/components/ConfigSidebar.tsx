"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, Users, CreditCard, Bell, Database } from "lucide-react";

const LINKS = [
  { href: "/config/empresa",       label: "Empresa",       icon: Building2 },
  { href: "/config/usuarios",      label: "Usuários",      icon: Users },
  { href: "/config/plano",         label: "Plano",         icon: CreditCard },
  { href: "/config/notificacoes",  label: "Notificações",  icon: Bell },
  { href: "/config/dados",         label: "Dados",         icon: Database },
];

export function ConfigSidebar() {
  const pathname = usePathname();
  return (
    <nav className="w-48 flex-shrink-0">
      <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-3 font-semibold">Configurações</p>
      <ul className="space-y-0.5">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <li key={href}>
              <Link
                href={href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                  active
                    ? "bg-blue-600/20 text-blue-400 font-medium"
                    : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
