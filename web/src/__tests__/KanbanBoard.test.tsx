import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { PipelineItem } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const item = (over: Partial<PipelineItem>): PipelineItem => ({
  run_id: "r", edital_id: "e", orgao: "Orgão X", objeto: "obj",
  valor_estimado_brl: 1000, stage: "analisando", bid_score: 0.8,
  created_at: null, deadline: null, ...over,
});

const items: PipelineItem[] = [
  item({ run_id: "r1", orgao: "Prefeitura A", stage: "analisando" }),
  item({ run_id: "r2", orgao: "Prefeitura B", stage: "decidindo" }),
  item({ run_id: "r3", orgao: "Prefeitura C", stage: "ganho" }),
];

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("KanbanBoard (AT-003 — render)", () => {
  it("renderiza as 6 colunas de estágio", () => {
    wrap(<KanbanBoard items={items} />);
    for (const label of ["Analisando", "Decidindo", "Preparando", "Disputando", "Ganho", "Perdido"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("posiciona cada card por estágio", () => {
    wrap(<KanbanBoard items={items} />);
    expect(screen.getByText("Prefeitura A")).toBeInTheDocument();
    expect(screen.getByText("Prefeitura B")).toBeInTheDocument();
    expect(screen.getByText("Prefeitura C")).toBeInTheDocument();
  });

  it("mostra o score do bid no card", () => {
    wrap(<KanbanBoard items={[item({ run_id: "x", bid_score: 0.8 })]} />);
    expect(screen.getByText("score 80")).toBeInTheDocument();
  });
});
