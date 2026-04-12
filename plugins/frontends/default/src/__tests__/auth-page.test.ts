import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../auth-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(props: Record<string, unknown> = {}): AnyEl {
  const el = document.createElement("shenas-auth-page") as AnyEl;
  Object.assign(el, props);
  document.body.appendChild(el);
  return el;
}

describe("shenas-auth-page", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ code: "ABC123", challenge: "test-challenge" }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-auth-page");
    expect(el.tagName.toLowerCase()).toBe("shenas-auth-page");
  });

  it("has default property values", () => {
    const el = mount() as AnyEl;
    expect(el.apiBase).toBe("");
    expect(el._authRequest).toBeNull();
    expect(el._error).toBeNull();
    expect(el._loading).toBe(true);
  });

  it("renders shadow root", async () => {
    const el = mount() as AnyEl;
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
  });

  it("calls auth/request on connect", async () => {
    const el = mount() as AnyEl;
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/auth/request", expect.objectContaining({ method: "POST" }));
  });

  it("setting _error updates shadow DOM", async () => {
    const el = mount() as AnyEl;
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    el._loading = false;
    el._error = "boom";
    await el.updateComplete;
    expect(el.shadowRoot?.textContent || "").toContain("boom");
  });
});
