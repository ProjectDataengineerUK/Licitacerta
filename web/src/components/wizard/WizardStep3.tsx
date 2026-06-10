"use client";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { SemaforoResult } from "./SemaforoResult";
import { api } from "@/lib/api";

interface Props {
  onBack: () => void;
  wizardData: Record<string, unknown>;
}

export function WizardStep3({ onBack, wizardData }: Props) {
  const [url, setUrl] = useState("");
  const [analisando, setAnalisando] = useState(false);
  const [resultado, setResultado] = useState<Record<string, unknown> | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [concluindo, setConcluindo] = useState(false);
  const [concluido, setConcluido] = useState(false);

  async function handleAnalise() {
    setAnalisando(true);
    setErro(null);
    try {
      const run = await api.submitEdital({ url, ...wizardData });
      await api.updateAtivacaoStep(3, { primeiro_edital_submetido: true, run_id_express: run.run_id });
      const snap = await api.getRunResult(run.run_id);
      setResultado(snap);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Falha ao analisar edital");
    } finally {
      setAnalisando(false);
    }
  }

  async function handleConcluir() {
    setConcluindo(true);
    try {
      await api.concluirAtivacao();
      setConcluido(true);
    } catch {
      // non-blocking
    } finally {
      setConcluindo(false);
    }
  }

  if (concluido) {
    return (
      <div className="text-center space-y-4 py-4">
        <div className="text-4xl">🎉</div>
        <h2 className="text-lg font-semibold text-zinc-100">Conta ativada!</h2>
        <p className="text-sm text-zinc-400">Você já pode usar todos os recursos da LicitaCerta.</p>
        <a href="/dashboard" className="block w-full bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold py-2.5 rounded-lg text-center">
          Ir para o Dashboard
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100 mb-1">Sua primeira análise</h2>
        <p className="text-sm text-zinc-400">
          Cole a URL de um edital ou envie um PDF para ver a IA em ação.
        </p>
      </div>
      {!resultado ? (
        <>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://pncp.gov.br/..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-500"
          />
          {erro && <p className="text-xs text-red-400">{erro}</p>}
          <div className="flex gap-2">
            <button
              onClick={onBack}
              className="flex-1 border border-zinc-700 text-zinc-400 text-sm py-2.5 rounded-lg hover:border-zinc-500"
            >
              Voltar
            </button>
            <button
              onClick={handleAnalise}
              disabled={!url || analisando}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-semibold py-2.5 rounded-lg flex items-center justify-center gap-2"
            >
              {analisando && <Loader2 className="w-4 h-4 animate-spin" />}
              {analisando ? "Analisando…" : "Analisar edital"}
            </button>
          </div>
        </>
      ) : (
        <>
          <SemaforoResult
            recommendation={String((resultado as any)?.bid_decision?.recommendation ?? "")}
            confidence={(resultado as any)?.bid_decision?.confidence}
            conclusion={(resultado as any)?.bid_decision?.conclusion}
          />
          <button
            onClick={handleConcluir}
            disabled={concluindo}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-semibold py-2.5 rounded-lg flex items-center justify-center gap-2"
          >
            {concluindo && <Loader2 className="w-4 h-4 animate-spin" />}
            Concluir ativação
          </button>
        </>
      )}
    </div>
  );
}
