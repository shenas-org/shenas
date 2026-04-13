import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../config-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-config") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-config", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { plugins: [] } }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-config");
    expect(el.tagName.toLowerCase()).toBe("shenas-config");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.kind).toBe("");
    expect(el.name).toBe("");
    expect(el._loading).toBe(true);
    expect(el._editing).toBeNull();
    expect(el._editValue).toBe("");
    expect(el._freqUnit).toBe("hours");
    expect(el._config).toBeNull();
  });

  it("fetches when kind and name set", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("_startEdit populates edit state for non-duration field", async () => {
    const el = mount();
    await el.updateComplete;
    el._startEdit("api_key", "abc");
    expect(el._editing).toBe("api_key");
    expect(el._editValue).toBe("abc");
  });

  it("_startEdit converts minutes to hours for duration fields", async () => {
    const el = mount();
    await el.updateComplete;
    el._startEdit("sync_frequency", "120");
    expect(el._freqNum).toBe("2");
    expect(el._freqUnit).toBe("hours");
  });

  it("_cancelEdit clears edit state", async () => {
    const el = mount();
    el._editing = "x";
    el._editValue = "y";
    el._cancelEdit();
    expect(el._editing).toBeNull();
    expect(el._editValue).toBe("");
  });
});
