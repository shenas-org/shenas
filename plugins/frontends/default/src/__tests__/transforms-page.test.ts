import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../transforms-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-transforms") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-transforms", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse({ data: { transforms: [] } }));
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-transforms");
    expect(el.tagName.toLowerCase()).toBe("shenas-transforms");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.source).toBe("");
    expect(el._transforms).toEqual([]);
    expect(el._loading).toBe(true);
    expect(el._editing).toBeNull();
    expect(el._editSql).toBe("");
    expect(el._message).toBeNull();
    expect(el._previewRows).toBeNull();
    expect(el._creating).toBe(false);
    expect(el._newForm).toEqual({
      source_duckdb_table: "",
      target_duckdb_table: "",
      description: "",
      materialization: "table",
      steps: [{ transformer: "sql", params: { mode: "builder" }, description: "" }],
    });
    expect(el._transformTypes).toEqual([]);
  });

  it("fetches on connect", async () => {
    mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("_emptyForm returns blank form", () => {
    const el = mount();
    const f = el._emptyForm();
    expect(f.source_duckdb_table).toBe("");
    expect(f.target_duckdb_table).toBe("");
    expect(f.description).toBe("");
    expect(f.steps).toEqual([{ transformer: "sql", params: { mode: "builder" }, description: "" }]);
  });

  it("renders shadow root", async () => {
    const el = mount();
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
  });

  it("_startEdit / _cancelEdit toggles edit state", () => {
    const el = mount();
    el._startEdit({
      id: 7,
      transformType: "sql",
      source: { id: "garmin.activities", schemaName: "garmin", tableName: "activities", displayName: "Activities" },
      target: { id: "datasets.exercise", schemaName: "datasets", tableName: "exercise", displayName: "Exercise" },
      sourcePlugin: "garmin",
      description: "test",
      params: '{"sql": "SELECT 1", "mode": "raw"}',
      sql: "SELECT 1",
      isDefault: false,
      enabled: true,
      steps: [],
    });
    expect(el._editing).toBe(7);
    expect(el._editSql).toBe("SELECT 1");
    expect(el._previewRows).toBeNull();
    el._cancelEdit();
    expect(el._editing).toBeNull();
    expect(el._editSql).toBe("");
    expect(el._previewRows).toBeNull();
  });

  it("_inspectTable dispatches inspect-table event", () => {
    const el = mount();
    const handler = vi.fn();
    el.addEventListener("inspect-table", handler);
    el._inspectTable("garmin", "activities");
    expect(handler).toHaveBeenCalled();
    const ev = handler.mock.calls[0][0];
    expect(ev.detail).toEqual({ schema: "garmin", table: "activities" });
  });
});
