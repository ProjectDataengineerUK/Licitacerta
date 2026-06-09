"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";

interface Props {
  params: Promise<{ id: string }>;
}

interface AcaoSugerida {
  label: string;
  rota?: string;
}

interface EvidenciaMentor {
  trecho: string;
  pagina?: number;
  fonte?: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tipo_resposta?: string;
  acoes_sugeridas?: AcaoSugerida[];
  evidencias?: EvidenciaMentor[];
  disclaimer?: string;
  streaming?: boolean;
}

const TIPO_COLORS: Record<string, string> = {
  juridico:    "bg-orange-100 text-orange-700",
  financeiro:  "bg-green-100 text-green-700",
  operacional: "bg-blue-100 text-blue-700",
  estrategico: "bg-purple-100 text-purple-700",
  geral:       "bg-gray-100 text-gray-600",
};

function TypingDots() {
  return (
    <span className="inline-flex gap-1 items-center h-4">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

export default function MentorPage({ params }: Props) {
  const { id } = use(params);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [todayCount, setTodayCount] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`/api/runs/${id}/mentor/history`)
      .then((r) => r.ok ? r.json() : { messages: [] })
      .then((data) => {
        if (data.messages?.length) {
          setMessages(data.messages);
          const userMsgs = data.messages.filter((m: ChatMessage) => m.role === "user");
          setTodayCount(userMsgs.length);
        }
      })
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const pergunta = input.trim();
    if (!pergunta || loading) return;
    setInput("");
    setLoading(true);

    const userMsg: ChatMessage = { role: "user", content: pergunta };
    setMessages((prev) => [...prev, userMsg, { role: "assistant", content: "", streaming: true }]);
    setTodayCount((c) => c + 1);

    try {
      const res = await fetch(`/api/runs/${id}/mentor/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "assistant", content: `Erro: ${err.detail || res.status}` },
        ]);
        setLoading(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamedText = "";
      let structuredData: Omit<ChatMessage, "role" | "content"> = {};

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: structured")) continue;
          if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            try {
              const parsed = JSON.parse(raw);
              if (parsed.text !== undefined) {
                streamedText += parsed.text;
                setMessages((prev) => [
                  ...prev.slice(0, -1),
                  { role: "assistant", content: streamedText, streaming: true },
                ]);
              } else {
                // structured event
                structuredData = {
                  tipo_resposta: parsed.tipo_resposta,
                  acoes_sugeridas: parsed.acoes_sugeridas,
                  evidencias: parsed.evidencias,
                  disclaimer: parsed.disclaimer,
                };
                const finalText = parsed.resposta || streamedText;
                setMessages((prev) => [
                  ...prev.slice(0, -1),
                  { role: "assistant", content: finalText, streaming: false, ...structuredData },
                ]);
              }
            } catch {
              // non-JSON line — skip
            }
          }
        }
      }

      if (streamedText && !structuredData.tipo_resposta) {
        setMessages((prev) => [
          ...prev.slice(0, -1),
          { role: "assistant", content: streamedText, streaming: false },
        ]);
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "Erro de conexão. Tente novamente." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-2xl mx-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-white flex items-center justify-between">
        <div>
          <Link href={`/runs/${id}/result`} className="text-xs text-gray-400 hover:text-gray-600">
            ← Resultado
          </Link>
          <h1 className="font-semibold text-gray-900 text-sm mt-0.5">Mentor LicitaCerta</h1>
        </div>
        <span className="text-xs text-gray-400">{todayCount}/50 hoje</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 text-sm py-12">
            <p className="font-medium mb-1">Olá! Sou o Mentor LicitaCerta.</p>
            <p>Faça uma pergunta sobre este edital.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm"
                  : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
              }`}
            >
              {msg.streaming && !msg.content ? (
                <TypingDots />
              ) : (
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              )}

              {msg.role === "assistant" && !msg.streaming && (
                <>
                  {msg.tipo_resposta && (
                    <span
                      className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium ${
                        TIPO_COLORS[msg.tipo_resposta] || TIPO_COLORS.geral
                      }`}
                    >
                      {msg.tipo_resposta}
                    </span>
                  )}

                  {msg.disclaimer && (
                    <div className="mt-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700">
                      {msg.disclaimer}
                    </div>
                  )}

                  {msg.acoes_sugeridas && msg.acoes_sugeridas.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Ações sugeridas
                      </p>
                      {msg.acoes_sugeridas.map((a, j) => (
                        a.rota ? (
                          <Link
                            key={j}
                            href={a.rota}
                            className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
                          >
                            <span>→</span> {a.label}
                          </Link>
                        ) : (
                          <p key={j} className="text-xs text-gray-600 flex items-center gap-1.5">
                            <span>•</span> {a.label}
                          </p>
                        )
                      ))}
                    </div>
                  )}

                  {msg.evidencias && msg.evidencias.length > 0 && (
                    <div className="mt-3 space-y-1.5">
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Evidências do edital
                      </p>
                      {msg.evidencias.map((e, j) => (
                        <div key={j} className="text-xs bg-gray-50 rounded px-2.5 py-1.5 border-l-2 border-blue-300">
                          <span className="text-gray-600 italic">"{e.trecho}"</span>
                          {e.pagina && <span className="text-gray-400 ml-2">p.{e.pagina}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
            placeholder="Faça uma pergunta sobre o edital…"
            disabled={loading}
            className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-xl px-4 py-2.5 text-sm font-medium transition-colors"
          >
            {loading ? "…" : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}
