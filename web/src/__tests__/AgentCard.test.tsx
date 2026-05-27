import { render, screen, fireEvent } from "@testing-library/react";
import { AgentCard } from "@/components/AgentCard";
import { describe, it, expect } from "vitest";

const noIssues = { conclusion: "Empresa elegível", confidence: 0.9, blocking_issues: [], warnings: [] };
const withIssues = { conclusion: "Pendências encontradas", confidence: 0.6, blocking_issues: ["Certidão vencida"], warnings: ["Prazo curto"] };

describe("AgentCard", () => {
  it("renders title", () => {
    render(<AgentCard title="Elegibilidade" data={noIssues} />);
    expect(screen.getByText("Elegibilidade")).toBeInTheDocument();
  });

  it("shows issue count badge when blocking issues exist", () => {
    render(<AgentCard title="Compliance" data={withIssues} />);
    expect(screen.getByText("1 issue")).toBeInTheDocument();
  });

  it("expands on click to show conclusion", () => {
    render(<AgentCard title="Elegibilidade" data={noIssues} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Empresa elegível")).toBeInTheDocument();
  });

  it("shows green dot when no blocking issues", () => {
    const { container } = render(<AgentCard title="T" data={noIssues} />);
    expect(container.querySelector(".bg-green-500")).toBeTruthy();
  });

  it("shows red dot when blocking issues exist", () => {
    const { container } = render(<AgentCard title="T" data={withIssues} />);
    expect(container.querySelector(".bg-red-500")).toBeTruthy();
  });
});
