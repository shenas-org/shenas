import { describe, it, expect, beforeEach, vi } from "vitest";
import "../shenas-frontends/shenas-page.ts";

type Page = HTMLElement & {
  loading: boolean;
  empty: boolean;
  loadingText: string;
  emptyText: string;
  displayName: string;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): Page {
  return document.createElement("shenas-page") as Page;
}

describe("shenas-page", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the element", () => {
    expect(customElements.get("shenas-page")).toBeTruthy();
  });

  it("has default property values", () => {
    const el = makeEl();
    expect(el.loading).toBe(false);
    expect(el.empty).toBe(false);
    expect(el.loadingText).toBe("Loading...");
    expect(el.emptyText).toBe("No data");
    expect(el.displayName).toBe("");
  });

  it("renders loading state", async () => {
    const el = makeEl();
    el.loading = true;
    el.loadingText = "Please wait";
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".loading")?.textContent).toBe("Please wait");
  });

  it("renders empty state when not loading", async () => {
    const el = makeEl();
    el.empty = true;
    el.emptyText = "Nothing";
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".empty")?.textContent).toBe("Nothing");
  });

  it("loading takes precedence over empty", async () => {
    const el = makeEl();
    el.loading = true;
    el.empty = true;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".loading")).toBeTruthy();
    expect(el.shadowRoot.querySelector(".empty")).toBeNull();
  });

  it("renders slot when neither loading nor empty", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("slot")).toBeTruthy();
  });

  it("dispatches page-title event when displayName changes", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    const handler = vi.fn();
    el.addEventListener("page-title", handler);
    el.displayName = "Dashboard";
    await el.updateComplete;
    expect(handler).toHaveBeenCalled();
    expect((handler.mock.calls[0][0] as CustomEvent).detail).toEqual({ title: "Dashboard" });
  });

  it("does not dispatch page-title for empty displayName", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    const handler = vi.fn();
    el.addEventListener("page-title", handler);
    await el.updateComplete;
    expect(handler).not.toHaveBeenCalled();
  });

  it("reflects loading attribute", async () => {
    const el = makeEl();
    el.loading = true;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.hasAttribute("loading")).toBe(true);
  });
});
