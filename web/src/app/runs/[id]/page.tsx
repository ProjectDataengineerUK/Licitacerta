"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useRun } from "@/lib/hooks/useRun";
import { ProgressTracker } from "@/components/ProgressTracker";
import { TERMINAL_STEPS } from "@/lib/types";

interface Props {
  params: Promise<{ id: string }>;
}

export default function RunStatusPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { data: run, isLoading } = useRun(id);

  if (run && TERMINAL_STEPS.has(run.current_step)) {
    router.replace(`/runs/${id}/result`);
    return null;
  }

  return (
    <div className="max-w-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Processando</h1>
        <p className="text-xs text-gray-400 font-mono mt-1">{id}</p>
      </div>

      {isLoading ? (
        <p className="text-gray-500 text-sm py-8 text-center">Conectando…</p>
      ) : (
        <div className="bg-white rounded-xl border p-6 shadow-sm">
          <ProgressTracker runId={id} currentStep={run?.current_step ?? ""} />
        </div>
      )}
    </div>
  );
}
