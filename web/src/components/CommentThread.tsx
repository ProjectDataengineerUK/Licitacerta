"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

interface RunComment {
  id: string; run_id: string; user_uid: string;
  texto: string; mencoes: string[]; deleted: boolean; created_at: string;
}

const POLL_MS = 15_000;

export function CommentThread({ runId, currentUid, role }: {
  runId: string;
  currentUid: string;
  role: "analista" | "operator" | "admin";
}) {
  const [comments, setComments] = useState<RunComment[]>([]);
  const [texto, setTexto] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.colaboracao.listComments(runId);
      setComments(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar comentários");
    }
  }, [runId]);

  useEffect(() => {
    void load();
    timer.current = setInterval(load, POLL_MS);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [load]);

  const submit = async () => {
    const t = texto.trim();
    if (!t) return;
    setLoading(true);
    try {
      await api.colaboracao.addComment(runId, t);
      setTexto("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao enviar");
    } finally {
      setLoading(false);
    }
  };

  const canDelete = (c: RunComment) =>
    !c.deleted && (c.user_uid === currentUid || role === "operator" || role === "admin");

  const remove = async (c: RunComment) => {
    try {
      await api.colaboracao.deleteComment(runId, c.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao remover");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-zinc-200">Comentários da equipe</h3>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <ul className="flex flex-col gap-2 max-h-96 overflow-y-auto">
        {comments.map((c) => (
          <li key={c.id}
            className={`rounded border border-zinc-700 bg-zinc-800/40 px-3 py-2 ${c.deleted ? "opacity-50 italic" : ""}`}>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-zinc-400">{c.user_uid}</span>
              <span className="text-[11px] text-zinc-500">{new Date(c.created_at).toLocaleString("pt-BR")}</span>
            </div>
            <p className="text-sm text-zinc-100 whitespace-pre-wrap">{c.texto}</p>
            {canDelete(c) && (
              <button onClick={() => remove(c)} className="mt-1 text-[11px] text-red-400 hover:text-red-300">
                Remover
              </button>
            )}
          </li>
        ))}
        {comments.length === 0 && <li className="text-xs text-zinc-500">Nenhum comentário ainda.</li>}
      </ul>
      <div className="flex flex-col gap-2">
        <textarea value={texto} maxLength={4000} onChange={(e) => setTexto(e.target.value)}
          placeholder="Escreva um comentário… use @ para mencionar a equipe"
          className="w-full resize-none rounded border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100"
          rows={3} />
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-zinc-500">{texto.length}/4000</span>
          <button onClick={submit} disabled={loading || !texto.trim()}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40">
            {loading ? "Enviando…" : "Comentar"}
          </button>
        </div>
      </div>
    </div>
  );
}
