import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch before importing the component
globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../app-shell.ts";

describe("shenas-app", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-app");
    expect(el).toBeDefined();
    expect(el.tagName.toLowerCase()).toBe("shenas-app");
  });

  it("has default api-base", () => {
    const el = document.createElement("shenas-app") as HTMLElement & { apiBase: string };
    expect(el.apiBase).toBe("/api");
  });

  it("fetches data on connect", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    const el = document.createElement("shenas-app");
    document.body.appendChild(el);

    // Wait for async fetch
    await new Promise((r) => setTimeout(r, 50));

    expect(globalThis.fetch).toHaveBeenCalled();
  });
});
