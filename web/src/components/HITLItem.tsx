"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { HITLItem as HITLItemType } from "@/lib/types";

interface HITLItemProps {
  item: HITLItemType;
  onDecision: () => void;
}

export function HITLItem({ item, onDecision }: HITLItemProps) {
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload = (() => {
    try {
      return JSON.parse(item.payload_json) as Record<string, unknown>;
    } catch {
      return {};
    }
  })();

  async function decide(action: "approve" | "reject") {
    setLoading(true);
    setError(null);
    try {
      if (action === "approve") {
        await api.approveHITL(item.run_id, notes);
      } else {
        await api.rejectHITL(item.run_id, notes);
      }
      onDecision();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao registrar decisão");
    } finally {
      setLoading(false);
    }
  }

  const bidDecision = payload.bid_decision as { recommendation?: string } | undefined;

  return (
    <div className="border rounded-lg p-4 space-y-3 bg-white">
      <div className="flex justify-between items-start">
        <div>
          <p className="font-medium text-sm">{item.action_required}</p>
          <p className="text-xs text-gray-500 font-mono">
            Run: {item.run_id.slice(0, 8)}…
          </p>
          <p className="text-xs text-gray-400">
            {new Date(item.created_at).toLocaleString("pt-BR")}
          </p>
        </div>
      </div>

      {bidDecision?.recommendation && (
        <p className="text-sm bg-blue-50 border border-blue-100 rounded px-3 py-2">
          Decisão do sistema:{" "}
          <span className="font-semibold">{bidDecision.recommendation}</span>
        </p>
      )}

      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Nota (opcional)"
        className="w-full border rounded px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />

      {error && <p className="text-red-500 text-xs">{error}</p>}

      <div className="flex gap-2">
        <button
          onClick={() => decide("approve")}
          disabled={loading}
          className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          Aprovar
        </button>
        <button
          onClick={() => decide("reject")}
          disabled={loading}
          className="flex-1 border border-red-300 text-red-600 hover:bg-red-50 rounded-lg py-2 text-sm font-medium disabled:opacity-50 transition-colors"
        >
          Reprovar
        </button>
      </div>
    </div>
  );
}
