import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TERMINAL_STEPS } from "@/lib/types";

export function useRun(id: string) {
  return useQuery({
    queryKey: ["run", id],
    queryFn: () => api.getRun(id),
    refetchInterval: (query) => {
      const step = query.state.data?.current_step ?? "";
      return TERMINAL_STEPS.has(step) ? false : 3000;
    },
  });
}

export function useRuns(stepFilter?: string) {
  return useQuery({
    queryKey: ["runs", stepFilter],
    queryFn: () => api.listRuns(stepFilter || undefined),
    refetchInterval: 15_000,
  });
}
