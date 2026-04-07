import { describe, it, expect, beforeEach, vi } from "vitest";
import "../shenas-frontends/status-toggle.ts";

type Toggle = HTMLElement & {
  enabled: boolean;
  toggleable: boolean;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): Toggle {
  return document.createElement("status-toggle") as Toggle;
}

describe("status-toggle", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the element", () => {
    expect(customElements.get("status-toggle")).toBeTruthy();
  });

  it("has default property values", () => {
    const el = makeEl();
    expect(el.enabled).toBe(false);
    expect(el.toggleable).toBe(false);
  });

  it("renders track and knob", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".track")).toBeTruthy();
    expect(el.shadowRoot.querySelector(".knob")).toBeTruthy();
  });

  it("reflects enabled attribute and sets title", async () => {
    const el = makeEl();
    el.enabled = true;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.hasAttribute("enabled")).toBe(true);
    expect(el.title).toBe("Enabled");
  });

  it("title is Disabled when not enabled", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.title).toBe("Disabled");
  });

  it("does not dispatch toggle when not toggleable", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("toggle", handler);
    (el.shadowRoot.querySelector(".track") as HTMLElement).click();
    expect(handler).not.toHaveBeenCalled();
  });

  it("dispatches toggle when toggleable and clicked", async () => {
    const el = makeEl();
    el.toggleable = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("toggle", handler);
    (el.shadowRoot.querySelector(".track") as HTMLElement).click();
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("reflects toggleable attribute", async () => {
    const el = makeEl();
    el.toggleable = true;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.hasAttribute("toggleable")).toBe(true);
  });
});
