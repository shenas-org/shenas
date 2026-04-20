import { describe, it, expect, vi, beforeEach } from "vitest";
import "../shenas-frontends/field.ts";

type Field = HTMLElement & {
  label: string;
  type: string;
  value: string;
  placeholder: string;
  readonly: boolean;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): Field {
  return document.createElement("shenas-field") as Field;
}

describe("shenas-field", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the custom element", () => {
    expect(customElements.get("shenas-field")).toBeTruthy();
  });

  it("has sensible default property values", () => {
    const el = makeEl();
    expect(el.label).toBe("");
    expect(el.type).toBe("text");
    expect(el.value).toBe("");
    expect(el.placeholder).toBe("");
    expect(el.readonly).toBe(false);
  });

  it("renders a label", async () => {
    const el = makeEl();
    el.label = "Name";
    document.body.appendChild(el);
    await el.updateComplete;
    const label = el.shadowRoot.querySelector("label");
    expect(label?.textContent).toContain("Name");
  });

  it("renders an input by default", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;
    const input = el.shadowRoot.querySelector("input");
    expect(input).toBeTruthy();
    expect(input?.type).toBe("text");
  });

  it("renders a textarea when type is textarea", async () => {
    const el = makeEl();
    el.type = "textarea";
    document.body.appendChild(el);
    await el.updateComplete;
    const textarea = el.shadowRoot.querySelector("textarea");
    expect(textarea).toBeTruthy();
    expect(el.shadowRoot.querySelector("input")).toBeNull();
  });

  it("renders a password input when type is password", async () => {
    const el = makeEl();
    el.type = "password";
    document.body.appendChild(el);
    await el.updateComplete;
    const input = el.shadowRoot.querySelector("input");
    expect(input?.type).toBe("password");
  });

  it("dispatches change event on input", async () => {
    const el = makeEl();
    document.body.appendChild(el);
    await el.updateComplete;

    const handler = vi.fn();
    el.addEventListener("change", handler);

    const input = el.shadowRoot.querySelector("input")!;
    input.value = "hello";
    input.dispatchEvent(new Event("input"));
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.value).toBe("hello");
  });

  it("dispatches change event on textarea input", async () => {
    const el = makeEl();
    el.type = "textarea";
    document.body.appendChild(el);
    await el.updateComplete;

    const handler = vi.fn();
    el.addEventListener("change", handler);

    const textarea = el.shadowRoot.querySelector("textarea")!;
    textarea.value = "text content";
    textarea.dispatchEvent(new Event("input"));
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.value).toBe("text content");
  });

  it("sets readonly on the input", async () => {
    const el = makeEl();
    el.readonly = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const input = el.shadowRoot.querySelector("input");
    expect(input?.readOnly).toBe(true);
  });

  it("sets placeholder on the input", async () => {
    const el = makeEl();
    el.placeholder = "Type here...";
    document.body.appendChild(el);
    await el.updateComplete;
    const input = el.shadowRoot.querySelector("input");
    expect(input?.placeholder).toBe("Type here...");
  });
});
