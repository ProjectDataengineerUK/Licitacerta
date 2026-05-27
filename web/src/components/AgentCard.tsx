"use client";

import { useState } from "react";

interface AgentCardProps {
  title: string;
  data: Record<string, unknown>;
}

export function AgentCard({ title, data }: AgentCardProps) {
  const [open, setOpen] = useState(false);

  const conclusion = data.conclusion as string | undefined;
  const confidence = data.confidence as number | undefined;
  const blocking = (data.blocking_issues as unknown[]) ?? [];
  const warnings = (data.warnings as string[]) ?? [];

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
              blocking.length > 0 ? "bg-red-500" : "bg-green-500"
            }`}
          />
          <span className="font-medium text-sm">{title}</span>
          {blocking.length > 0 && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
              {blocking.length} issue{blocking.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <span className="text-gray-400 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t px-4 py-3 space-y-2 bg-gray-50 text-sm">
          {conclusion && <p className="text-gray-700">{conclusion}</p>}
          {confidence !== undefined && (
            <p className="text-xs text-gray-500">
              Confiança: {(confidence * 100).toFixed(0)}%
            </p>
          )}
          {blocking.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-600 mb-1">Issues bloqueantes:</p>
              {blocking.map((issue, i) => (
                <p key={i} className="text-xs text-red-500 font-mono">
                  {typeof issue === "object" ? JSON.stringify(issue) : String(issue)}
                </p>
              ))}
            </div>
          )}
          {warnings.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-yellow-600 mb-1">Alertas:</p>
              {warnings.map((w, i) => (
                <p key={i} className="text-xs text-yellow-700">{w}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
