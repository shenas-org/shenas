import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch before importing the component
global.fetch = vi.fn();

import "../app-shell.js";

describe("shenas-app", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    global.fetch.mockResolvedValue({
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
    const el = document.createElement("shenas-app");
    expect(el.apiBase).toBe("/api");
  });

  it("fetches data on connect", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    const el = document.createElement("shenas-app");
    document.body.appendChild(el);

    // Wait for async fetch
    await new Promise((r) => setTimeout(r, 50));

    expect(global.fetch).toHaveBeenCalled();
  });
});
