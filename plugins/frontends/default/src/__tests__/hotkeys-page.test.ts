import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../hotkeys-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-hotkeys") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-hotkeys", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { hotkeys: {} } }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-hotkeys");
    expect(el.tagName.toLowerCase()).toBe("shenas-hotkeys");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.actions).toEqual([]);
    expect(el._bindings).toEqual({});
    expect(el._recording).toBeNull();
    expect(el._recordedKey).toBe("");
    expect(el._conflict).toBeNull();
    expect(el._loading).toBe(true);
    expect(el._filter).toBe("");
  });

  it("fetches bindings on connect", async () => {
    mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("_startRecording / _stopRecording toggles state", async () => {
    const el = mount();
    el._startRecording("action.foo");
    expect(el._recording).toBe("action.foo");
    expect(el._recordedKey).toBe("");
    el._stopRecording();
    expect(el._recording).toBeNull();
  });

  it("renders filter input in shadow DOM", async () => {
    const el = mount();
    el._loading = false;
    el.actions = [{ id: "a.b", label: "Do thing", category: "Test" }];
    await el.updateComplete;
    const input = el.shadowRoot?.querySelector(".filter-input");
    expect(input).toBeTruthy();
  });
});
