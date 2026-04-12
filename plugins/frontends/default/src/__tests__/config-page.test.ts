import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

// Stub localStorage for happy-dom
const localStorageStore: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem(key: string) {
    return localStorageStore[key] ?? null;
  },
  setItem(key: string, value: string) {
    localStorageStore[key] = value;
  },
  removeItem(key: string) {
    delete localStorageStore[key];
  },
  clear() {
    Object.keys(localStorageStore).forEach((k) => delete localStorageStore[k]);
  },
};

import "../config-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-config-page") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-config-page", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ configs: [] }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-config-page");
    expect(el.tagName.toLowerCase()).toBe("shenas-config-page");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("");
    expect(el._configs).toEqual([]);
    expect(el._error).toBeNull();
    expect(el._loading).toBe(true);
    expect(el._editingKey).toBeNull();
  });

  it("fetches configs on connect", async () => {
    const el = mount();
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("startEdit sets editingKey", async () => {
    const el = mount();
    await el.updateComplete;
    el.startEdit("api_key");
    expect(el._editingKey).toBe("api_key");
  });

  it("cancelEdit clears editingKey", async () => {
    const el = mount();
    el._editingKey = "x";
    el.cancelEdit();
    expect(el._editingKey).toBeNull();
  });
});
