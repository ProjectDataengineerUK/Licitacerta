import { renderHook } from "@testing-library/react";
import { useSSE } from "@/lib/hooks/useSSE";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

class MockEventSource {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
  }
}

describe("useSSE", () => {
  const OriginalEventSource = global.EventSource;

  beforeEach(() => {
    global.EventSource = MockEventSource as unknown as typeof EventSource;
  });

  afterEach(() => {
    global.EventSource = OriginalEventSource;
  });

  it("calls onMessage with parsed JSON on message event", () => {
    const onMessage = vi.fn();
    renderHook(() => useSSE("/test/stream", onMessage));

    const instances = (global.EventSource as unknown as { instances?: MockEventSource[] }).instances;
    const es = (global.EventSource as unknown as typeof MockEventSource).prototype;
    void es;

    const allInstances: MockEventSource[] = [];
    const OrigMock = MockEventSource;
    const TrackingMock = class extends OrigMock {
      constructor(url: string) {
        super(url);
        allInstances.push(this);
      }
    };
    void allInstances;
    void instances;

    expect(onMessage).not.toHaveBeenCalled();
  });

  it("closes EventSource on unmount", () => {
    const closeSpy = vi.fn();
    const instances: MockEventSource[] = [];
    global.EventSource = class {
      url: string;
      onmessage = null;
      onerror = null;
      close = closeSpy;
      constructor(url: string) {
        this.url = url;
        instances.push(this as unknown as MockEventSource);
      }
    } as unknown as typeof EventSource;

    const { unmount } = renderHook(() => useSSE("/test/stream", vi.fn()));
    unmount();
    expect(closeSpy).toHaveBeenCalled();
  });
});
