import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, apiFetchFull, renderMessage, registerCommands, openExternal } from "../shenas-frontends/api.ts";

const mockFetch = vi.fn();

beforeEach(() => {
  globalThis.fetch = mockFetch as unknown as typeof fetch;
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

describe("apiFetch", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ hello: "world" }));
    const result = await apiFetch<{ hello: string }>("/api", "/test");
    expect(result).toEqual({ hello: "world" });
    expect(mockFetch).toHaveBeenCalledWith("/api/test", { method: "GET" });
  });

  it("returns null on non-2xx", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(null, false, 500));
    const result = await apiFetch("/api", "/fail");
    expect(result).toBeNull();
  });

  it("sends JSON body for non-GET", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await apiFetch("/api", "/post", { method: "POST", json: { key: "val" } });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/post",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ key: "val" }),
      }),
    );
  });
});

describe("apiFetchFull", () => {
  it("returns ok=true with data on success", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ x: 1 }));
    const result = await apiFetchFull<{ x: number }>("/api", "/data");
    expect(result).toEqual({ ok: true, status: 200, data: { x: 1 } });
  });

  it("returns ok=false with status on error", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ error: "bad" }, false, 400));
    const result = await apiFetchFull("/api", "/bad");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(400);
  });
});

describe("renderMessage", () => {
  it("returns empty string for null/undefined", () => {
    expect(renderMessage(null)).toBe("");
    expect(renderMessage(undefined)).toBe("");
  });

  it("returns a TemplateResult for a message", () => {
    const result = renderMessage({ type: "error", text: "oops" });
    expect(typeof result).toBe("object");
  });
});

describe("registerCommands", () => {
  it("dispatches a register-command custom event", () => {
    const el = document.createElement("div");
    let captured: CustomEvent | null = null;
    el.addEventListener("register-command", (e) => {
      captured = e as CustomEvent;
    });
    registerCommands(el, "test-component", [{ id: "act1", label: "Action 1", category: "Test" }]);
    expect(captured).not.toBeNull();
    expect((captured as unknown as CustomEvent).detail).toEqual({
      componentId: "test-component",
      commands: [{ id: "act1", label: "Action 1", category: "Test" }],
    });
  });
});

describe("openExternal", () => {
  it("opens a new tab in browser", () => {
    const openSpy = vi.spyOn(window, "open").mockReturnValue(null);
    openExternal("https://example.com");
    expect(openSpy).toHaveBeenCalledWith("https://example.com", "_blank", "noopener");
    openSpy.mockRestore();
  });

  it("uses Tauri invoke when available", async () => {
    const invokeMock = vi.fn().mockResolvedValue(undefined);
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = { invoke: invokeMock };
    openExternal("https://example.com");
    expect(invokeMock).toHaveBeenCalledWith("plugin:shell|open", { path: "https://example.com" });
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
  });
});
