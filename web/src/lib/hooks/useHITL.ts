import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useHITL() {
  return useQuery({
    queryKey: ["hitl"],
    queryFn: () => api.listHITL(),
    refetchInterval: 10_000,
  });
}
