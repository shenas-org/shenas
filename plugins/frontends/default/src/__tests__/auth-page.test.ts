import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../auth-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(props: Record<string, unknown> = {}): AnyEl {
  const el = document.createElement("shenas-auth") as AnyEl;
  Object.assign(el, props);
  document.body.appendChild(el);
  return el;
}

describe("shenas-auth", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockResponse({ data: { plugins: [{ name: "garmin", authFields: [], authInstructions: "" }] } }),
    );
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-auth");
    expect(el.tagName.toLowerCase()).toBe("shenas-auth");
  });

  it("has default property values", () => {
    const el = mount() as AnyEl;
    expect(el.apiBase).toBe("/api");
    expect(el.sourceName).toBe("");
    expect(el._fields).toEqual([]);
    expect(el._loading).toBe(false);
    expect(el._needsMfa).toBe(false);
    expect(el._submitting).toBe(false);
    expect(el._stored).toEqual([]);
    expect(el._message).toBeNull();
  });

  it("renders shadow root", async () => {
    const el = mount() as AnyEl;
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
  });

  it("fetches fields when sourceName is set", async () => {
    const el = mount() as AnyEl;
    el.sourceName = "garmin";
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("setting _message updates shadow DOM", async () => {
    const el = mount() as AnyEl;
    await el.updateComplete;
    el._message = { type: "error", text: "boom" };
    await el.updateComplete;
    expect(el.shadowRoot?.textContent || "").toContain("boom");
  });
});
