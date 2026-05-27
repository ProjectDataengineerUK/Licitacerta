import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SubmitForm } from "@/components/SubmitForm";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));
vi.mock("@/lib/api", () => ({
  api: { analyze: vi.fn().mockResolvedValue({ run_id: "run-001" }) },
}));

describe("SubmitForm", () => {
  beforeEach(() => mockPush.mockClear());

  it("disables submit when fields are empty", () => {
    render(<SubmitForm />);
    expect(screen.getByRole("button", { name: /analisar/i })).toBeDisabled();
  });

  it("enables submit when both fields filled", async () => {
    render(<SubmitForm />);
    fireEvent.change(screen.getByPlaceholderText(/00\.000/), { target: { value: "12.345.678/0001-90" } });
    fireEvent.change(screen.getByPlaceholderText(/cole aqui/i), { target: { value: "Texto do edital" } });
    expect(screen.getByRole("button", { name: /analisar/i })).not.toBeDisabled();
  });

  it("redirects to run page on success", async () => {
    render(<SubmitForm />);
    fireEvent.change(screen.getByPlaceholderText(/00\.000/), { target: { value: "12.345.678/0001-90" } });
    fireEvent.change(screen.getByPlaceholderText(/cole aqui/i), { target: { value: "Texto do edital" } });
    fireEvent.click(screen.getByRole("button", { name: /analisar/i }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/runs/run-001"));
  });
});
