import { describe, it, expect, beforeEach, vi } from "vitest";
import { html } from "lit";
import "../shenas-frontends/data-list.ts";
import type { DataListColumn } from "../shenas-frontends/data-list.ts";

type Row = Record<string, unknown>;
type DataList = HTMLElement & {
  columns: DataListColumn[];
  rows: Row[];
  rowClass: ((row: Row) => string) | null;
  actions: ((row: Row) => unknown) | null;
  emptyText: string;
  showAdd: boolean;
  updateComplete: Promise<boolean>;
  shadowRoot: ShadowRoot;
};

function makeEl(): DataList {
  return document.createElement("shenas-data-list") as DataList;
}

describe("shenas-data-list", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("registers the element", () => {
    expect(customElements.get("shenas-data-list")).toBeTruthy();
  });

  it("has default property values", () => {
    const el = makeEl();
    expect(el.columns).toEqual([]);
    expect(el.rows).toEqual([]);
    expect(el.emptyText).toBe("No items");
    expect(el.showAdd).toBe(false);
  });

  it("renders empty state when no rows", async () => {
    const el = makeEl();
    el.emptyText = "Nothing here";
    document.body.appendChild(el);
    await el.updateComplete;
    const empty = el.shadowRoot.querySelector(".empty");
    expect(empty?.textContent).toContain("Nothing here");
  });

  it("renders rows and columns", async () => {
    const el = makeEl();
    el.columns = [
      { key: "name", label: "Name" },
      { key: "version", label: "Version", class: "mono" },
    ];
    el.rows = [
      { name: "foo", version: "1.0" },
      { name: "bar", version: "2.0" },
    ];
    document.body.appendChild(el);
    await el.updateComplete;
    const ths = el.shadowRoot.querySelectorAll("th");
    expect(ths.length).toBe(2);
    expect(ths[0].textContent).toBe("Name");
    const trs = el.shadowRoot.querySelectorAll("tbody tr");
    expect(trs.length).toBe(2);
    const monoCells = el.shadowRoot.querySelectorAll("td.mono");
    expect(monoCells.length).toBe(2);
  });

  it("uses custom render function for cells", async () => {
    const el = makeEl();
    el.columns = [{ key: "name", label: "Name", render: (row) => html`<b>${row.name}</b>` }];
    el.rows = [{ name: "hi" }];
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("td b")?.textContent).toBe("hi");
  });

  it("applies rowClass function", async () => {
    const el = makeEl();
    el.columns = [{ key: "n", label: "N" }];
    el.rows = [{ n: 1, on: false }];
    el.rowClass = (r) => (r.on ? "" : "disabled-row");
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("tr.disabled-row")).toBeTruthy();
  });

  it("renders actions column when actions provided", async () => {
    const el = makeEl();
    el.columns = [{ key: "n", label: "N" }];
    el.rows = [{ n: 1 }];
    el.actions = () => html`<button>Edit</button>`;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("td.actions-cell button")).toBeTruthy();
    // header has extra empty cell
    expect(el.shadowRoot.querySelectorAll("th").length).toBe(2);
  });

  it("shows add button when showAdd is true and dispatches add event", async () => {
    const el = makeEl();
    el.showAdd = true;
    document.body.appendChild(el);
    await el.updateComplete;
    const btn = el.shadowRoot.querySelector(".add-btn") as HTMLButtonElement;
    expect(btn).toBeTruthy();
    const handler = vi.fn();
    el.addEventListener("add", handler);
    btn.click();
    expect(handler).toHaveBeenCalled();
  });

  it("shows add button alongside table with rows", async () => {
    const el = makeEl();
    el.columns = [{ key: "n", label: "N" }];
    el.rows = [{ n: 1 }];
    el.showAdd = true;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot.querySelector("table")).toBeTruthy();
    expect(el.shadowRoot.querySelector(".add-btn")).toBeTruthy();
  });
});
