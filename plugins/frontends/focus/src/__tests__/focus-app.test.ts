import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../focus-app.ts";

describe("shenas-focus", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: {} }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-focus");
    expect(el).toBeDefined();
    expect(el.tagName.toLowerCase()).toBe("shenas-focus");
  });

  it("has expected default property values", () => {
    const el = document.createElement("shenas-focus") as HTMLElement & {
      apiBase: string;
      _activeIndex: number;
      _loading: boolean;
      _paletteOpen: boolean;
    };
    expect(el.apiBase).toBe("/api");
    expect(el._activeIndex).toBe(0);
    expect(el._loading).toBe(true);
    expect(el._paletteOpen).toBe(false);
  });

  it("fetches data on connect", async () => {
    const el = document.createElement("shenas-focus");
    document.body.appendChild(el);
    await new Promise((r) => setTimeout(r, 50));
    expect(globalThis.fetch).toHaveBeenCalled();
  });
});
