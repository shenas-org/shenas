import { describe, it, expect, vi, beforeEach } from "vitest";
import "../shenas-frontends/multi-select.ts";

type MultiSelect = HTMLElement & {
  label: string;
  value: string[];
  options: { value: string; label: string }[];
  _filter: string;
  _toggle: (value: string) => void;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): MultiSelect {
  return document.createElement("shenas-multi-select") as MultiSelect;
}

describe("shenas-multi-select", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the custom element", () => {
    expect(customElements.get("shenas-multi-select")).toBeTruthy();
  });

  it("has sensible default property values", () => {
    const el = makeEl();
    expect(el.label).toBe("");
    expect(el.value).toEqual([]);
    expect(el.options).toEqual([]);
    expect(el._filter).toBe("");
  });

  it("renders a label", async () => {
    const el = makeEl();
    el.label = "Cities";
    document.body.appendChild(el);
    await el.updateComplete;
    const label = el.shadowRoot.querySelector(".label");
    expect(label?.textContent).toContain("Cities");
  });

  it("renders options as checkboxes", async () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
    ];
    document.body.appendChild(el);
    await el.updateComplete;
    const opts = el.shadowRoot.querySelectorAll(".option");
    expect(opts.length).toBe(2);
    expect(opts[0]?.textContent?.trim()).toContain("Alpha");
  });

  it("checks selected options", async () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
    ];
    el.value = ["b"];
    document.body.appendChild(el);
    await el.updateComplete;
    const checkboxes = el.shadowRoot.querySelectorAll("input[type=checkbox]") as NodeListOf<HTMLInputElement>;
    expect(checkboxes[0]?.checked).toBe(false);
    expect(checkboxes[1]?.checked).toBe(true);
  });

  it("shows count of selected", async () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
      { value: "c", label: "Gamma" },
    ];
    el.value = ["a", "c"];
    document.body.appendChild(el);
    await el.updateComplete;
    const count = el.shadowRoot.querySelector(".count");
    expect(count?.textContent).toContain("2 of 3 selected");
  });

  // -- toggle -----------------------------------------------------------

  it("adds value on toggle when unchecked", () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "A" },
      { value: "b", label: "B" },
    ];
    el.value = ["a"];
    const handler = vi.fn();
    el.addEventListener("change", handler);
    el._toggle("b");
    expect(el.value).toEqual(["a", "b"]);
    expect(handler).toHaveBeenCalled();
    expect(handler.mock.calls[0][0].detail.value).toEqual(["a", "b"]);
  });

  it("removes value on toggle when checked", () => {
    const el = makeEl();
    el.options = [
      { value: "a", label: "A" },
      { value: "b", label: "B" },
    ];
    el.value = ["a", "b"];
    el._toggle("a");
    expect(el.value).toEqual(["b"]);
  });

  it("toggles to empty when last item unchecked", () => {
    const el = makeEl();
    el.value = ["a"];
    el._toggle("a");
    expect(el.value).toEqual([]);
  });

  // -- filter -----------------------------------------------------------

  it("does not show search for 8 or fewer options", async () => {
    const el = makeEl();
    el.options = Array.from({ length: 8 }, (_, i) => ({ value: `v${i}`, label: `Item ${i}` }));
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".search")).toBeNull();
  });

  it("shows search for more than 8 options", async () => {
    const el = makeEl();
    el.options = Array.from({ length: 9 }, (_, i) => ({ value: `v${i}`, label: `Item ${i}` }));
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector(".search")).toBeTruthy();
  });

  it("filters options by label", async () => {
    const el = makeEl();
    el.options = Array.from({ length: 10 }, (_, i) => ({ value: `v${i}`, label: `Item ${i}` }));
    el._filter = "Item 3";
    document.body.appendChild(el);
    await el.updateComplete;
    const opts = el.shadowRoot.querySelectorAll(".option");
    expect(opts.length).toBe(1);
    expect(opts[0]?.textContent?.trim()).toContain("Item 3");
  });

  it("filter is case-insensitive", async () => {
    const el = makeEl();
    el.options = Array.from({ length: 10 }, (_, i) => ({ value: `v${i}`, label: `City ${i}` }));
    el._filter = "city 5";
    document.body.appendChild(el);
    await el.updateComplete;
    const opts = el.shadowRoot.querySelectorAll(".option");
    expect(opts.length).toBe(1);
  });
});
