import type { UserRole } from "@/lib/types";

const META: Record<UserRole, { label: string; cls: string }> = {
  admin:       { label: "Admin",       cls: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  analista:    { label: "Analista",    cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  visualizador:{ label: "Visualizador",cls: "bg-zinc-700/50 text-zinc-400 border-zinc-600" },
};

export function RoleBadge({ papel }: { papel: UserRole }) {
  const { label, cls } = META[papel] ?? META.visualizador;
  return (
    <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${cls}`}>
      {label}
    </span>
  );
}
