"use client";

import { useState } from "react";

interface AgentCardProps {
  title: string;
  data: Record<string, unknown>;
  icon?: string;
}

export function AgentCard({ title, data, icon }: AgentCardProps) {
  const [open, setOpen] = useState(false);

  const conclusion = data.conclusion as string | undefined;
  const confidence = data.confidence as number | undefined;
  const blocking = (data.blocking_issues as unknown[]) ?? [];
  const warnings = (data.warnings as string[]) ?? [];
  const riskLevel = data.risk_level as string | undefined;

  const hasIssues = blocking.length > 0;
  const confPct = confidence !== undefined ? Math.round(confidence * 100) : null;

  const statusColor = hasIssues
    ? "bg-red-500"
    : riskLevel === "high" || riskLevel === "critical"
    ? "bg-orange-400"
    : "bg-green-500";

  const confBarColor =
    confPct === null
      ? "bg-gray-300"
      : confPct >= 80
      ? "bg-green-500"
      : confPct >= 60
      ? "bg-yellow-400"
      : "bg-red-400";

  return (
    <div className="border rounded-xl overflow-hidden bg-white shadow-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusColor}`} />
        <span className="flex items-center gap-2 flex-1 min-w-0">
          {icon && <span className="text-base">{icon}</span>}
          <span className="font-semibold text-sm text-gray-800">{title}</span>
          {hasIssues && (
            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
              {blocking.length} bloqueante{blocking.length > 1 ? "s" : ""}
            </span>
          )}
          {warnings.length > 0 && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
              {warnings.length} alerta{warnings.length > 1 ? "s" : ""}
            </span>
          )}
        </span>

        {confPct !== null && (
          <div className="flex items-center gap-2 flex-shrink-0 mr-2">
            <div className="w-24 h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${confBarColor}`}
                style={{ width: `${confPct}%` }}
              />
            </div>
            <span className="text-xs text-gray-500 w-8 text-right">{confPct}%</span>
          </div>
        )}

        <span className="text-gray-300 text-xs flex-shrink-0">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="border-t px-5 py-4 space-y-3 bg-gray-50 text-sm">
          {conclusion && (
            <p className="text-gray-700 leading-relaxed">{conclusion}</p>
          )}

          {blocking.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 space-y-1.5">
              <p className="text-xs font-semibold text-red-700 flex items-center gap-1">
                <span>⛔</span> Issues bloqueantes
              </p>
              {blocking.map((issue, i) => (
                <p key={i} className="text-xs text-red-600 pl-4">
                  {typeof issue === "object" && issue !== null && "description" in issue
                    ? String((issue as Record<string, unknown>).description)
                    : typeof issue === "object"
                    ? JSON.stringify(issue)
                    : String(issue)}
                </p>
              ))}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 space-y-1.5">
              <p className="text-xs font-semibold text-yellow-700 flex items-center gap-1">
                <span>⚠️</span> Alertas
              </p>
              {warnings.map((w, i) => (
                <p key={i} className="text-xs text-yellow-700 pl-4">{w}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
