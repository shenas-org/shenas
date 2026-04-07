import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, apiFetchFull, gql, gqlFull, renderMessage, registerCommands } from "../shenas-frontends/api.ts";

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

describe("gql", () => {
  it("returns data on success", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ data: { plugins: [] } }));
    const result = await gql<{ plugins: unknown[] }>("/api", "{ plugins { name } }");
    expect(result).toEqual({ plugins: [] });
  });

  it("returns null on errors in response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ errors: [{ message: "bad query" }] }));
    const result = await gql("/api", "{ broken }");
    expect(result).toBeNull();
  });

  it("returns null on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(null, false, 500));
    const result = await gql("/api", "{ x }");
    expect(result).toBeNull();
  });
});

describe("gqlFull", () => {
  it("returns ok=true with data on success", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ data: { x: 1 } }));
    const result = await gqlFull<{ x: number }>("/api", "query");
    expect(result.ok).toBe(true);
    expect(result.data).toEqual({ x: 1 });
    expect(result.errors).toEqual([]);
  });

  it("returns ok=false with errors", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ errors: [{ message: "bad" }] }));
    const result = await gqlFull("/api", "query");
    expect(result.ok).toBe(false);
    expect(result.errors).toEqual([{ message: "bad" }]);
  });

  it("returns ok=false on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(null, false, 503));
    const result = await gqlFull("/api", "query");
    expect(result.ok).toBe(false);
    expect(result.errors[0]?.message).toBe("HTTP 503");
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
    registerCommands(el, "test-component", [
      { id: "act1", label: "Action 1", category: "Test" },
    ]);
    expect(captured).not.toBeNull();
    expect((captured as unknown as CustomEvent).detail).toEqual({
      componentId: "test-component",
      commands: [{ id: "act1", label: "Action 1", category: "Test" }],
    });
  });
});
