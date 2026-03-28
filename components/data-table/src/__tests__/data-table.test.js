import { describe, it, expect, vi, beforeEach } from "vitest";
import { tableFromArrays } from "apache-arrow";
import {
  createTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
} from "@tanstack/table-core";

// Test TanStack Table logic independently of Lit rendering

function makeTestData() {
  return [
    { date: "2026-03-15", mood: 7, stress: 3, exercise: 1 },
    { date: "2026-03-16", mood: 5, stress: 6, exercise: 0 },
    { date: "2026-03-17", mood: 8, stress: 2, exercise: 1 },
    { date: "2026-03-18", mood: 4, stress: 8, exercise: 0 },
    { date: "2026-03-19", mood: 9, stress: 1, exercise: 1 },
  ];
}

function makeColumns() {
  return [
    { id: "date", accessorKey: "date", header: "date" },
    { id: "mood", accessorKey: "mood", header: "mood" },
    { id: "stress", accessorKey: "stress", header: "stress" },
    { id: "exercise", accessorKey: "exercise", header: "exercise" },
  ];
}

function makeTable(overrides = {}) {
  let sorting = [];
  let columnFilters = [];
  let pagination = { pageIndex: 0, pageSize: 3 };

  return createTable({
    state: { sorting, columnFilters, pagination, ...overrides.state },
    data: overrides.data || makeTestData(),
    columns: overrides.columns || makeColumns(),
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: (updater) => {
      sorting = typeof updater === "function" ? updater(sorting) : updater;
    },
    onColumnFiltersChange: (updater) => {
      columnFilters = typeof updater === "function" ? updater(columnFilters) : updater;
    },
    onPaginationChange: (updater) => {
      pagination = typeof updater === "function" ? updater(pagination) : updater;
    },
  });
}

describe("TanStack Table core", () => {
  it("creates a table with correct row count", () => {
    const table = makeTable();
    expect(table.getCoreRowModel().rows.length).toBe(5);
  });

  it("paginates correctly", () => {
    const table = makeTable();
    const rows = table.getRowModel().rows;
    expect(rows.length).toBe(3); // pageSize = 3
    expect(table.getPageCount()).toBe(2);
  });

  it("sorts ascending by mood", () => {
    const table = makeTable({
      state: { sorting: [{ id: "mood", desc: false }], columnFilters: [], pagination: { pageIndex: 0, pageSize: 10 } },
    });
    const moods = table.getRowModel().rows.map((r) => r.getValue("mood"));
    expect(moods).toEqual([4, 5, 7, 8, 9]);
  });

  it("sorts descending by stress", () => {
    const table = makeTable({
      state: { sorting: [{ id: "stress", desc: true }], columnFilters: [], pagination: { pageIndex: 0, pageSize: 10 } },
    });
    const stresses = table.getRowModel().rows.map((r) => r.getValue("stress"));
    expect(stresses).toEqual([8, 6, 3, 2, 1]);
  });

  it("filters by column value", () => {
    const table = makeTable({
      state: {
        sorting: [],
        columnFilters: [{ id: "exercise", value: "1" }],
        pagination: { pageIndex: 0, pageSize: 10 },
      },
    });
    const rows = table.getFilteredRowModel().rows;
    expect(rows.length).toBe(3);
    rows.forEach((r) => expect(String(r.getValue("exercise"))).toContain("1"));
  });

  it("returns correct page count with filter", () => {
    const table = makeTable({
      state: {
        sorting: [],
        columnFilters: [{ id: "exercise", value: "1" }],
        pagination: { pageIndex: 0, pageSize: 2 },
      },
    });
    expect(table.getPageCount()).toBe(2); // 3 filtered rows / pageSize 2
  });
});

describe("Arrow IPC parsing", () => {
  it("converts arrow table to column names", () => {
    const arrowTable = tableFromArrays({
      date: ["2026-03-15", "2026-03-16"],
      mood: [7, 5],
    });
    const columns = arrowTable.schema.fields.map((f) => f.name);
    expect(columns).toEqual(["date", "mood"]);
  });

  it("converts arrow table to row objects", () => {
    const arrowTable = tableFromArrays({
      date: ["2026-03-15"],
      mood: [7],
    });
    const rows = [];
    for (let i = 0; i < arrowTable.numRows; i++) {
      const row = {};
      for (const field of arrowTable.schema.fields) {
        row[field.name] = arrowTable.getChild(field.name).get(i);
      }
      rows.push(row);
    }
    expect(rows).toEqual([{ date: "2026-03-15", mood: 7 }]);
  });
});

describe("Cell formatting", () => {
  // Test the formatting logic used by the component
  function formatCell(value) {
    if (value == null) return "";
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    if (typeof value === "bigint") return value.toString();
    return String(value);
  }

  it("formats null as empty string", () => {
    expect(formatCell(null)).toBe("");
    expect(formatCell(undefined)).toBe("");
  });

  it("formats numbers", () => {
    expect(formatCell(42)).toBe("42");
  });

  it("formats strings", () => {
    expect(formatCell("hello")).toBe("hello");
  });

  it("formats bigint", () => {
    expect(formatCell(42n)).toBe("42");
  });

  it("formats dates", () => {
    expect(formatCell(new Date("2026-03-15T00:00:00Z"))).toBe("2026-03-15");
  });
});
