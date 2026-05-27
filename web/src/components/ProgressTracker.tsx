"use client";

import { useState } from "react";
import { useSSE } from "@/lib/hooks/useSSE";
import { tokenStore } from "@/lib/token-store";
import { SUBGRAPH_STEPS } from "@/lib/types";
import type { StepStatus } from "@/lib/types";

const STEP_ORDER = Object.entries(SUBGRAPH_STEPS).sort(
  (a, b) => a[1].order - b[1].order
);

function getStatus(stepKey: string, currentStep: string): StepStatus {
  const current = SUBGRAPH_STEPS[currentStep]?.order ?? 0;
  const step = SUBGRAPH_STEPS[stepKey]?.order ?? 0;
  if (stepKey === currentStep) return "running";
  if (step < current) return "completed";
  return "pending";
}

const STATUS_STYLE: Record<StepStatus, string> = {
  completed: "bg-green-50 border-green-300",
  running:   "bg-blue-50  border-blue-400",
  pending:   "bg-gray-50  border-gray-200",
  error:     "bg-red-50   border-red-300",
};

const STATUS_ICON: Record<StepStatus, string> = {
  completed: "✓",
  running:   "⏳",
  pending:   "○",
  error:     "✗",
};

const STATUS_TEXT: Record<StepStatus, string> = {
  completed: "text-green-700",
  running:   "text-blue-700 font-semibold",
  pending:   "text-gray-400",
  error:     "text-red-700",
};

interface ProgressTrackerProps {
  runId: string;
  currentStep: string;
}

export function ProgressTracker({ runId, currentStep }: ProgressTrackerProps) {
  const [liveStep, setLiveStep] = useState(currentStep);
  const token = tokenStore.get();

  useSSE(
    `/api/proxy/runs/${runId}/stream?token=${encodeURIComponent(token)}`,
    (data) => {
      if (data && typeof data === "object" && "step" in data) {
        setLiveStep(data.step as string);
      }
    }
  );

  return (
    <div className="space-y-2">
      {STEP_ORDER.map(([key, { label }]) => {
        const status = getStatus(key, liveStep);
        return (
          <div
            key={key}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border transition-all ${STATUS_STYLE[status]}`}
          >
            <span className="text-base w-5 text-center">{STATUS_ICON[status]}</span>
            <span className={`text-sm ${STATUS_TEXT[status]}`}>{label}</span>
            {status === "running" && (
              <span className="ml-auto text-xs text-blue-500 animate-pulse">
                processando…
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
