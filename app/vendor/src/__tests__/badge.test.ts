import { describe, it, expect, beforeEach } from "vitest";
import "../shenas-frontends/badge.ts";

type Badge = HTMLElement & {
  variant: string;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): Badge {
  return document.createElement("shenas-badge") as Badge;
}

describe("shenas-badge", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the custom element", () => {
    expect(customElements.get("shenas-badge")).toBeTruthy();
  });

  it("has empty variant by default", () => {
    const el = makeEl();
    expect(el.variant).toBe("");
  });

  it("renders slotted content", async () => {
    const el = makeEl();
    el.textContent = "enabled";
    document.body.appendChild(el);
    await el.updateComplete;
    const slot = el.shadowRoot.querySelector("slot");
    expect(slot).toBeTruthy();
  });

  it("reflects variant as attribute", async () => {
    const el = makeEl();
    el.variant = "success";
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.getAttribute("variant")).toBe("success");
  });

  it("accepts all known variants without error", () => {
    const el = makeEl();
    for (const variant of ["success", "error", "warning", "info", "debug", ""]) {
      el.variant = variant;
      expect(el.variant).toBe(variant);
    }
  });
});
