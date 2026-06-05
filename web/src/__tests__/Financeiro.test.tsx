import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FinanceiroPage from "@/app/financeiro/page";
import type { ContractDashboard } from "@/lib/types";

const dash: ContractDashboard = {
  total_contratado_brl: 80000,
  recebido_brl: 30000,
  a_receber_brl: 50000,
  em_atraso_brl: 0,
  vencendo_30d: 1,
};

vi.mock("@/lib/api", () => ({
  api: {
    getContractsDashboard: vi.fn(() => Promise.resolve(dash)),
    listContractAlerts: vi.fn(() => Promise.resolve([])),
  },
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Financeiro (AT-005)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mostra receita contratada total de R$80k", async () => {
    wrap(<FinanceiroPage />);
    await waitFor(() => expect(screen.getByText(/80\.000/)).toBeInTheDocument());
  });

  it("mostra contagem de contratos vencendo em 30d", async () => {
    wrap(<FinanceiroPage />);
    await waitFor(() => expect(screen.getByText(/contrato vencendo/, { selector: "p" })).toBeInTheDocument());
  });
});
