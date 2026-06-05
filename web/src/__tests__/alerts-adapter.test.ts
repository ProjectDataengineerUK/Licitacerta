import { describe, it, expect } from "vitest";
import { buildUnifiedAlerts } from "@/lib/alerts-adapter";
import type { Alert, Certidao, ContractAlert, Prediction } from "@/lib/types";

const alert = (over: Partial<Alert> = {}): Alert => ({
  id: "a1", tenant_id: "t1", tipo: "x", severidade: "warning",
  titulo: "Alerta sistema", mensagem: "msg", link_relativo: "/runs/1",
  entidade_tipo: null, entidade_id: null, lido: false, created_at: "", ...over,
});

const contractAlert = (over: Partial<ContractAlert> = {}): ContractAlert => ({
  contract_id: "c1", tipo: "vencimento_contrato", severity: "critical",
  mensagem: "Contrato vence", prazo_dias: 3, acao_sugerida: "Renovar", ...over,
});

const certidao = (over: Partial<Certidao> = {}): Certidao => ({
  id: "ce1", tipo: "CND", status: "expiring_soon",
  valid_until: new Date(Date.now() + 5 * 86400000).toISOString(),
  gcs_path: "", created_at: "", ...over,
});

const prediction = (over: Partial<Prediction> = {}): Prediction => ({
  id: "p1", orgao_nome: "Prefeitura", objeto_previsto: "Material",
  valor_estimado_brl: 1000, data_prevista_publicacao: "2026-07-01",
  confianca_pct: 80, fonte: "pca", dias_antecedencia: 20, status: "previsto", ...over,
});

describe("buildUnifiedAlerts", () => {
  it("normaliza as 4 fontes em UnifiedAlert", () => {
    const out = buildUnifiedAlerts({
      alerts: [alert()],
      contractAlerts: [contractAlert()],
      certidoes: [certidao()],
      predictions: [prediction()],
    });
    const sources = out.map((a) => a.source).sort();
    expect(sources).toEqual(["alert", "certidao", "contract", "prediction"]);
  });

  it("ordena por severidade (critical primeiro) e depois por prazo", () => {
    const out = buildUnifiedAlerts({
      alerts: [alert({ severidade: "info" })],
      contractAlerts: [contractAlert({ severity: "critical", prazo_dias: 3 })],
      certidoes: [certidao({ status: "expired" })], // critical, prazo negativo (vencida)
    });
    // dois criticals primeiro; certidão vencida (prazo<atual) vem antes do contrato (3d)
    expect(out[0].severity).toBe("critical");
    expect(out[1].severity).toBe("critical");
    expect(out[out.length - 1].severity).toBe("info");
  });

  it("só permite mark-read na fonte 'alert'", () => {
    const out = buildUnifiedAlerts({
      alerts: [alert()],
      contractAlerts: [contractAlert()],
    });
    expect(out.find((a) => a.source === "alert")!.canMarkRead).toBe(true);
    expect(out.find((a) => a.source === "contract")!.canMarkRead).toBe(false);
  });

  it("ignora alertas de sistema já lidos", () => {
    const out = buildUnifiedAlerts({ alerts: [alert({ lido: true })] });
    expect(out).toHaveLength(0);
  });

  it("ignora certidões válidas (não vencidas/a vencer)", () => {
    const out = buildUnifiedAlerts({ certidoes: [certidao({ status: "valid" })] });
    expect(out).toHaveLength(0);
  });

  it("deriva severidade da certidão a partir do status", () => {
    const expired = buildUnifiedAlerts({ certidoes: [certidao({ status: "expired" })] });
    const soon = buildUnifiedAlerts({ certidoes: [certidao({ status: "expiring_soon" })] });
    expect(expired[0].severity).toBe("critical");
    expect(soon[0].severity).toBe("warning");
  });
});
