import { render, screen } from "@testing-library/react";
import { BidBanner } from "@/components/BidBanner";
import { describe, it, expect } from "vitest";

describe("BidBanner", () => {
  it("renders participar recommendation", () => {
    render(<BidBanner recommendation="participar" confidence={0.87} summary="Edital favorável à empresa" />);
    expect(screen.getByText("Participar")).toBeInTheDocument();
    expect(screen.getByText(/Edital favorável/)).toBeInTheDocument();
  });

  it("renders nao_participar recommendation", () => {
    render(<BidBanner recommendation="nao_participar" confidence={0.5} summary="Risco alto" />);
    expect(screen.getByText("Não Participar")).toBeInTheDocument();
  });

  it("shows confidence as percentage", () => {
    render(<BidBanner recommendation="participar" confidence={0.87} summary="ok" />);
    expect(screen.getByText(/87%/)).toBeInTheDocument();
  });

  it("renders impugnar recommendation", () => {
    render(<BidBanner recommendation="impugnar" confidence={0.75} summary="Cláusula restritiva" />);
    expect(screen.getByText("Impugnar")).toBeInTheDocument();
  });
});
