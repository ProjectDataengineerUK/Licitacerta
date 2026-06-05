import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Cockpit } from "@/components/Cockpit";
import type { DashboardSummary, HealthScore } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const summary: DashboardSummary = {
  pipeline: { analisando: 2, decidindo: 1, preparando: 0, disputando: 1, ganho_mes: 3, perdido_mes: 1 },
  financeiro: { receita_contratada_brl: 150000, a_receber_30d_brl: 50000, a_receber_60d_brl: 30000 },
  taxa_vitoria_pct: 75,
  alertas_criticos: 2,
  alertas_warning: 1,
};

const health: HealthScore = {
  score: 82, label: "saudável", componentes: [], recomendacoes: [], delta_semana: 5, calculado_em: "",
};

vi.mock("@/lib/api", () => ({
  api: {
    getDashboardSummary: vi.fn(() => Promise.resolve(summary)),
    getHealthScore: vi.fn(() => Promise.resolve(health)),
  },
}));

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("Cockpit (AT-001)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("mostra KPIs do summary", async () => {
    wrap(<Cockpit />);
    await waitFor(() => expect(screen.getByText("75%")).toBeInTheDocument()); // taxa de vitória
    expect(screen.getByText("4")).toBeInTheDocument(); // em disputa = 2+1+0+1
    expect(screen.getAllByText("2")[0]).toBeInTheDocument(); // alertas críticos (also in pipeline grid)
  });

  it("mostra o health score", async () => {
    wrap(<Cockpit />);
    await waitFor(() => expect(screen.getByText("82")).toBeInTheDocument());
    expect(screen.getByText("saudável")).toBeInTheDocument();
  });
});
