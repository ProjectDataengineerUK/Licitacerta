"use client";
// Edge middleware.ts cannot read localStorage auth token — redirect must be client-side
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const PUBLIC_PATHS = ["/login", "/signup", "/welcome"];

export function ActivationGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  const { data } = useQuery({
    queryKey: ["ativacao-status"],
    queryFn: () => api.getAtivacaoStatus(),
    enabled: !isPublic,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!isPublic && data && data.ativado === false) {
      router.replace("/welcome");
    }
  }, [data, isPublic, router]);

  return <>{children}</>;
}
