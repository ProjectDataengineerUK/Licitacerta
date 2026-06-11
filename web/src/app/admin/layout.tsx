"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Users, ScrollText, ShieldAlert, LogOut } from "lucide-react";

const LINKS = [
  { href: "/admin/metricas", label: "Métricas", icon: LayoutDashboard },
  { href: "/admin/tenants", label: "Tenants", icon: Users },
  { href: "/admin/logs", label: "Audit Log", icon: ScrollText },
];

function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    document.cookie = "admin_key=; path=/; max-age=0";
    sessionStorage.removeItem("admin_key");
    router.push("/admin/login");
  }

  return (
    <aside className="w-44 shrink-0">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-7 h-7 rounded-lg bg-red-700 flex items-center justify-center">
          <ShieldAlert className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-zinc-100 text-sm">Admin</span>
      </div>
      <nav className="space-y-0.5">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                active
                  ? "bg-red-700/20 text-red-400"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <button
        onClick={logout}
        className="mt-8 flex items-center gap-2 text-xs text-zinc-600 hover:text-zinc-300 px-3 py-2 transition-colors"
      >
        <LogOut className="w-3 h-3" />
        Sair
      </button>
    </aside>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-8">
      <AdminSidebar />
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
