"use client";

import { useHITL } from "@/lib/hooks/useHITL";
import { HITLItem } from "@/components/HITLItem";

export default function HITLPage() {
  const { data, isLoading, refetch } = useHITL();
  const items = data?.items ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Aprovações Pendentes</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Decisões que requerem revisão humana antes de prosseguir.
        </p>
      </div>

      {isLoading ? (
        <p className="text-gray-500 text-sm py-8 text-center">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center">
          Nenhuma aprovação pendente.
        </p>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <HITLItem
              key={item.id}
              item={item}
              onDecision={() => refetch()}
            />
          ))}
        </div>
      )}
    </div>
  );
}
