import { describe, it, expect, vi, beforeEach } from "vitest";
import "../shenas-frontends/dropdown.ts";

type Dropdown = HTMLElement & {
  label: string;
  value: string;
  placeholder: string;
  options: { value: string; label: string; disabled?: boolean }[];
  disabled: boolean;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): Dropdown {
  return document.createElement("shenas-dropdown") as Dropdown;
}

describe("shenas-dropdown", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the custom element", () => {
    expect(customElements.get("shenas-dropdown")).toBeTruthy();
  });

  it("has sensible default property values", () => {
    const el = makeEl();
    expect(el.label).toBe("");
    expect(el.value).toBe("");
    expect(el.placeholder).toBe("");
    expect(el.options).toEqual([]);
    expect(el.disabled).toBe(false);
  });

  it("renders a label", async () => {
    const el = makeEl();
    el.label = "Pick one";
    document.body.appendChild(el);
    await el.updateComplete;
    const label = el.shadowRoot.querySelector("label");
    expect(label?.textContent).toContain("Pick one");
  });

  it("renders options", async () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
    ];
    document.body.appendChild(el);
    await el.updateComplete;
    const opts = el.shadowRoot.querySelectorAll("option");
    expect(opts.length).toBe(2);
    expect(opts[0]?.textContent?.trim()).toBe("Alpha");
  });

  it("renders placeholder option when set", async () => {
    const el = makeEl();
    el.placeholder = "Select...";
    el.options = [{ value: "x", label: "X" }];
    document.body.appendChild(el);
    await el.updateComplete;
    const opts = el.shadowRoot.querySelectorAll("option");
    expect(opts.length).toBe(2);
    expect(opts[0]?.textContent?.trim()).toBe("Select...");
    expect(opts[0]?.disabled).toBe(true);
  });

  it("dispatches change event on selection", async () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "A" },
      { value: "b", label: "B" },
    ];
    document.body.appendChild(el);
    await el.updateComplete;

    const handler = vi.fn();
    el.addEventListener("change", handler);

    const select = el.shadowRoot.querySelector("select")!;
    select.value = "b";
    select.dispatchEvent(new Event("change"));
    expect(handler).toHaveBeenCalled();
    expect(el.value).toBe("b");
  });

  it("disables the select when disabled property is true", async () => {
    const el = makeEl();
    el.disabled = true;
    el.options = [{ value: "x", label: "X" }];
    document.body.appendChild(el);
    await el.updateComplete;
    const select = el.shadowRoot.querySelector("select");
    expect(select?.disabled).toBe(true);
  });
});
