import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

class MockEventSource {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  close(): void {}
}
globalThis.EventSource = MockEventSource as unknown as typeof EventSource;

import "../logs-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-logs") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-logs", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
      json: () => Promise.resolve({}),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-logs");
    expect(el.tagName.toLowerCase()).toBe("shenas-logs");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.pipe).toBe("");
    expect(el._activeTab).toBe("logs");
    expect(el._logs).toEqual([]);
    expect(el._spans).toEqual([]);
    expect(el._loading).toBe(true);
    expect(el._search).toBe("");
    expect(el._severity).toBe("");
    expect(el._expanded).toBeNull();
    expect(el._live).toBe(false);
  });

  it("opens EventSource streams on connect", () => {
    const el = mount();
    expect(el._logSource).toBeInstanceOf(MockEventSource);
    expect(el._spanSource).toBeInstanceOf(MockEventSource);
  });

  it("disconnect closes streams", () => {
    const el = mount();
    el.remove();
    expect(el._logSource).toBeNull();
    expect(el._spanSource).toBeNull();
  });

  it("renders tab buttons", async () => {
    const el = mount();
    await el.updateComplete;
    const tabs = el.shadowRoot?.querySelectorAll(".tab");
    expect(tabs && tabs.length).toBeGreaterThan(0);
  });
});
