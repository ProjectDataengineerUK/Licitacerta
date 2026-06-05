import { render, screen, fireEvent } from "@testing-library/react";
import { AgentCard } from "@/components/AgentCard";
import { describe, it, expect } from "vitest";

// AT-004 — Resultado com evidências
const withEvidence = {
  conclusion: "Cláusula restritiva detectada",
  confidence: 0.7,
  risk_level: "high",
  blocking_issues: [
    {
      description: "Exigência de atestado incompatível",
      severity: "blocking",
      evidence: { document: "edital.pdf", page: 12, excerpt: "exige atestado de capacidade técnica..." },
    },
  ],
  warnings: [],
  evidence: [{ document: "edital.pdf", page: 5, excerpt: "objeto da licitação" }],
};

describe("AgentCard — evidências (AT-004)", () => {
  it("mostra referência de página no issue bloqueante", () => {
    render(<AgentCard title="Conformidade" data={withEvidence} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Exigência de atestado incompatível")).toBeInTheDocument();
    expect(screen.getAllByText(/ver p\.12 do edital/).length).toBeGreaterThan(0);
  });

  it("mostra bloco de evidências top-level com trecho e página", () => {
    render(<AgentCard title="Conformidade" data={withEvidence} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/objeto da licitação/)).toBeInTheDocument();
    expect(screen.getByText(/ver p\.5 do edital/)).toBeInTheDocument();
  });

  it("é retrocompatível com blocking_issues como strings", () => {
    render(<AgentCard title="X" data={{ conclusion: "c", blocking_issues: ["texto simples"], warnings: [] }} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("texto simples")).toBeInTheDocument();
  });
});
