import type {
  Alert, Certidao, ContractAlert, Prediction, UnifiedAlert,
} from "./types";

/* ──────────────────────────────────────────────────────────────────────
 * Normaliza as 4 fontes de alerta (shapes divergentes — ver DESIGN/ADR-002)
 * em UnifiedAlert. Só `source === "alert"` é marcável como lido.
 * ────────────────────────────────────────────────────────────────────── */

const SEVERITY_RANK: Record<UnifiedAlert["severity"], number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

function fromAlert(a: Alert): UnifiedAlert {
  return {
    id: `alert:${a.id}`,
    source: "alert",
    severity: a.severidade,
    title: a.titulo,
    message: a.mensagem,
    href: a.link_relativo ?? undefined,
    canMarkRead: true,
  };
}

function fromContractAlert(c: ContractAlert): UnifiedAlert {
  return {
    id: `contract:${c.contract_id}:${c.tipo}`,
    source: "contract",
    severity: c.severity,
    title: c.tipo === "pagamento_atrasado" ? "Pagamento atrasado" : "Vencimento de contrato",
    message: c.mensagem,
    prazoDias: c.prazo_dias ?? undefined,
    href: "/financeiro",
    action: c.acao_sugerida,
    canMarkRead: false,
  };
}

function diasAte(iso: string | null): number | undefined {
  if (!iso) return undefined;
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return undefined;
  return Math.ceil((d - Date.now()) / 86_400_000);
}

function fromCertidao(c: Certidao): UnifiedAlert | null {
  if (c.status !== "expired" && c.status !== "expiring_soon") return null;
  const expired = c.status === "expired";
  return {
    id: `certidao:${c.id}`,
    source: "certidao",
    severity: expired ? "critical" : "warning",
    title: expired ? `Certidão ${c.tipo} vencida` : `Certidão ${c.tipo} vencendo`,
    message: c.valid_until
      ? `Válida até ${new Date(c.valid_until).toLocaleDateString("pt-BR")}`
      : "Sem data de validade registrada",
    prazoDias: diasAte(c.valid_until),
    href: "/certidoes",
    action: "Renovar",
    canMarkRead: false,
  };
}

function fromPrediction(p: Prediction): UnifiedAlert {
  // Editais previstos pelo radar PCA: severidade por proximidade/confiança.
  const severity: UnifiedAlert["severity"] =
    p.dias_antecedencia <= 7 ? "warning" : "info";
  const orgao = p.orgao_nome ?? "Órgão não identificado";
  const objeto = p.objeto_previsto ?? "objeto não previsto";
  return {
    id: `prediction:${p.id}`,
    source: "prediction",
    severity,
    title: `Edital previsto — ${orgao}`,
    message: `${objeto} · confiança ${Math.round(p.confianca_pct)}%`,
    prazoDias: p.dias_antecedencia,
    href: "/watch",
    action: "Ver previsão",
    canMarkRead: false,
  };
}

export function buildUnifiedAlerts(sources: {
  alerts?: Alert[];
  contractAlerts?: ContractAlert[];
  certidoes?: Certidao[];
  predictions?: Prediction[];
}): UnifiedAlert[] {
  const out: UnifiedAlert[] = [];

  for (const a of sources.alerts ?? []) {
    if (!a.lido) out.push(fromAlert(a));
  }
  for (const c of sources.contractAlerts ?? []) out.push(fromContractAlert(c));
  for (const c of sources.certidoes ?? []) {
    const u = fromCertidao(c);
    if (u) out.push(u);
  }
  for (const p of sources.predictions ?? []) out.push(fromPrediction(p));

  // Ordena: severidade (critical→info), depois menor prazo primeiro.
  return out.sort((a, b) => {
    const sev = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    if (sev !== 0) return sev;
    const pa = a.prazoDias ?? Number.POSITIVE_INFINITY;
    const pb = b.prazoDias ?? Number.POSITIVE_INFINITY;
    return pa - pb;
  });
}
