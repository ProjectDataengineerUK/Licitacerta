import { render, screen } from "@testing-library/react";
import { RunTable } from "@/components/RunTable";
import type { RunStatus } from "@/lib/types";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const runs: RunStatus[] = [
  {
    run_id: "abc123def456",
    edital_id: "edital-xyz-000001234567",
    current_step: "completed",
    bid_decision: { recommendation: "participar", confidence: 0.9, summary: "", score: 8 },
    pricing: null,
    errors: [],
  },
];

describe("RunTable", () => {
  it("renders empty state", () => {
    render(<RunTable runs={[]} />);
    expect(screen.getByText(/Nenhum run/)).toBeInTheDocument();
  });

  it("renders run row with truncated edital_id", () => {
    render(<RunTable runs={runs} />);
    expect(screen.getByText(/edital-xyz-000001234/)).toBeInTheDocument();
  });

  it("shows bid decision recommendation", () => {
    render(<RunTable runs={runs} />);
    expect(screen.getByText("participar")).toBeInTheDocument();
  });
});
