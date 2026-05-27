"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useHITL } from "@/lib/hooks/useHITL";
import { useAuth } from "@/components/providers";
import { signOutUser } from "@/lib/firebase";

const LINKS = [
  { href: "/", label: "Analisar" },
  { href: "/runs", label: "Histórico" },
  { href: "/hitl", label: "Aprovações" },
  { href: "/watch", label: "Watch" },
  { href: "/certidoes", label: "Certidões" },
  { href: "/contracts", label: "Contratos" },
];

export function NavBar() {
  const pathname = usePathname();
  const { data } = useHITL();
  const { user } = useAuth();
  const pendingCount = data?.items.length ?? 0;

  return (
    <nav className="border-b bg-white sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
        <div className="flex items-center gap-6">
          <span className="font-bold text-blue-600 text-lg">LicitaCerta AI</span>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm flex items-center gap-1 transition-colors ${
                pathname === link.href
                  ? "text-blue-600 font-medium"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {link.label}
              {link.href === "/hitl" && pendingCount > 0 && (
                <span className="bg-orange-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[18px] text-center leading-tight">
                  {pendingCount}
                </span>
              )}
            </Link>
          ))}
        </div>
        {user && (
          <button
            onClick={signOutUser}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Sair
          </button>
        )}
      </div>
    </nav>
  );
}
