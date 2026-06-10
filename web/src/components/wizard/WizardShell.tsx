"use client";
import React from "react";

interface Props {
  step: number;
  totalSteps: number;
  children: React.ReactNode;
}

export function WizardShell({ step, totalSteps, children }: Props) {
  const progress = (step / totalSteps) * 100;

  return (
    <div className="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-6">
      <div className="mb-6">
        <div className="flex justify-between text-xs text-zinc-500 mb-1.5">
          <span>Passo {step} de {totalSteps}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      {children}
    </div>
  );
}
