import { useEffect, useRef } from "react";

export function useSSE(url: string, onMessage: (data: unknown) => void) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (e: MessageEvent) => {
      try {
        onMessageRef.current(JSON.parse(e.data as string));
      } catch {
        // mensagem não-JSON ignorada
      }
    };
    return () => es.close();
  }, [url]);
}
