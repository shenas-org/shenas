import { describe, it, expect, beforeEach, vi } from "vitest";
import "../shenas-frontends/form-panel.ts";

type FormPanel = HTMLElement & {
  title: string;
  submitLabel: string;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): FormPanel {
  return document.createElement("shenas-form-panel") as FormPanel;
}

describe("shenas-form-panel", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the element", () => {
    expect(customElements.get("shenas-form-panel")).toBeTruthy();
  });

  it("has default property values", () => {
    const el = makeEl();
    expect(el.title).toBe("");
    expect(el.submitLabel).toBe("Save");
  });

  it("renders title when set", async () => {
    const el = makeEl();
    el.title = "My Form";
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("h3")?.textContent).toBe("My Form");
  });

  it("does not render h3 when title empty", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("h3")).toBeNull();
  });

  it("renders submit and cancel buttons", async () => {
    const el = makeEl();
    el.submitLabel = "Create";
    document.body.appendChild(el);
    await el.updateComplete;
    const buttons = el.shadowRoot.querySelectorAll("button");
    expect(buttons.length).toBe(2);
    expect(buttons[0].textContent).toBe("Create");
    expect(buttons[1].textContent).toBe("Cancel");
  });

  it("dispatches submit event on submit click", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("submit", handler);
    (el.shadowRoot.querySelectorAll("button")[0] as HTMLButtonElement).click();
    expect(handler).toHaveBeenCalled();
  });

  it("dispatches cancel event on cancel click", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    const handler = vi.fn();
    el.addEventListener("cancel", handler);
    (el.shadowRoot.querySelectorAll("button")[1] as HTMLButtonElement).click();
    expect(handler).toHaveBeenCalled();
  });

  it("renders default slot", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("slot")).toBeTruthy();
  });
});
