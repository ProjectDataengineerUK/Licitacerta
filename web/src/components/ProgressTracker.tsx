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

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "completed") {
    return (
      <span className="flex items-center justify-center w-8 h-8 rounded-full bg-green-500 text-white text-sm font-bold flex-shrink-0">
        ✓
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 flex-shrink-0">
        <span className="w-3 h-3 rounded-full bg-white animate-ping" />
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="flex items-center justify-center w-8 h-8 rounded-full bg-red-500 text-white text-sm font-bold flex-shrink-0">
        ✗
      </span>
    );
  }
  return (
    <span className="flex items-center justify-center w-8 h-8 rounded-full border-2 border-gray-200 bg-white flex-shrink-0">
      <span className="w-2 h-2 rounded-full bg-gray-300" />
    </span>
  );
}

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
    <div className="relative">
      {/* vertical connector line */}
      <div className="absolute left-4 top-4 bottom-4 w-px bg-gray-200" />

      <div className="space-y-1">
        {STEP_ORDER.map(([key, { label }]) => {
          const status = getStatus(key, liveStep);

          return (
            <div key={key} className="relative flex items-start gap-4 pb-1">
              <StepIcon status={status} />
              <div
                className={`flex-1 flex items-center justify-between py-1.5 px-4 rounded-lg min-h-[40px] transition-all ${
                  status === "running"
                    ? "bg-blue-50 border border-blue-200"
                    : status === "completed"
                    ? "bg-transparent"
                    : "bg-transparent"
                }`}
              >
                <span
                  className={`text-sm transition-all ${
                    status === "running"
                      ? "text-blue-700 font-semibold"
                      : status === "completed"
                      ? "text-gray-700"
                      : "text-gray-400"
                  }`}
                >
                  {label}
                </span>
                {status === "running" && (
                  <span className="text-xs text-blue-500 animate-pulse ml-2 whitespace-nowrap">
                    processando…
                  </span>
                )}
                {status === "completed" && (
                  <span className="text-xs text-green-500 ml-2">concluído</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
