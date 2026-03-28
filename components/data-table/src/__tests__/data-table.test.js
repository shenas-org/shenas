import { describe, it, expect } from "vitest";
import { tableFromArrays } from "apache-arrow";

function makeTestData() {
  return [
    { date: "2026-03-15", mood: 7, stress: 3, exercise: 1 },
    { date: "2026-03-16", mood: 5, stress: 6, exercise: 0 },
    { date: "2026-03-17", mood: 8, stress: 2, exercise: 1 },
    { date: "2026-03-18", mood: 4, stress: 8, exercise: 0 },
    { date: "2026-03-19", mood: 9, stress: 1, exercise: 1 },
  ];
}

// Test the sorting/filtering/pagination logic used by the component

function filterData(data, filters) {
  return data.filter((row) =>
    Object.entries(filters).every(([col, val]) => {
      if (!val) return true;
      const cell = row[col];
      return cell != null && String(cell).toLowerCase().includes(val.toLowerCase());
    })
  );
}

function sortData(data, sortCol, sortDesc) {
  if (!sortCol) return data;
  return [...data].sort((a, b) => {
    const va = a[sortCol], vb = b[sortCol];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (va < vb) return sortDesc ? 1 : -1;
    if (va > vb) return sortDesc ? -1 : 1;
    return 0;
  });
}

function pageData(data, page, pageSize) {
  return data.slice(page * pageSize, (page + 1) * pageSize);
}

describe("Sorting", () => {
  it("sorts ascending by mood", () => {
    const sorted = sortData(makeTestData(), "mood", false);
    expect(sorted.map((r) => r.mood)).toEqual([4, 5, 7, 8, 9]);
  });

  it("sorts descending by stress", () => {
    const sorted = sortData(makeTestData(), "stress", true);
    expect(sorted.map((r) => r.stress)).toEqual([8, 6, 3, 2, 1]);
  });

  it("returns unsorted when no sort column", () => {
    const data = makeTestData();
    const sorted = sortData(data, null, false);
    expect(sorted.map((r) => r.mood)).toEqual([7, 5, 8, 4, 9]);
  });

  it("handles null values", () => {
    const data = [{ v: null }, { v: 2 }, { v: 1 }];
    const sorted = sortData(data, "v", false);
    expect(sorted.map((r) => r.v)).toEqual([1, 2, null]);
  });
});

describe("Filtering", () => {
  it("filters by string match", () => {
    const data = makeTestData();
    const filtered = filterData(data, { date: "03-17" });
    expect(filtered.length).toBe(1);
    expect(filtered[0].date).toBe("2026-03-17");
  });

  it("filters by number as string", () => {
    const filtered = filterData(makeTestData(), { exercise: "1" });
    expect(filtered.length).toBe(3);
  });

  it("returns all with empty filter", () => {
    const filtered = filterData(makeTestData(), { mood: "" });
    expect(filtered.length).toBe(5);
  });

  it("is case insensitive", () => {
    const data = [{ name: "Alice" }, { name: "Bob" }];
    const filtered = filterData(data, { name: "alice" });
    expect(filtered.length).toBe(1);
  });
});

describe("Pagination", () => {
  it("returns first page", () => {
    const paged = pageData(makeTestData(), 0, 3);
    expect(paged.length).toBe(3);
    expect(paged[0].mood).toBe(7);
  });

  it("returns second page", () => {
    const paged = pageData(makeTestData(), 1, 3);
    expect(paged.length).toBe(2);
    expect(paged[0].mood).toBe(4);
  });

  it("returns empty for out of range page", () => {
    const paged = pageData(makeTestData(), 10, 3);
    expect(paged.length).toBe(0);
  });
});

describe("Arrow IPC parsing", () => {
  it("converts arrow table to column names", () => {
    const table = tableFromArrays({ date: ["2026-03-15"], mood: [7] });
    expect(table.schema.fields.map((f) => f.name)).toEqual(["date", "mood"]);
  });

  it("converts arrow table to row objects", () => {
    const table = tableFromArrays({ date: ["2026-03-15"], mood: [7] });
    const rows = [];
    for (let i = 0; i < table.numRows; i++) {
      const row = {};
      for (const field of table.schema.fields) {
        row[field.name] = table.getChild(field.name).get(i);
      }
      rows.push(row);
    }
    expect(rows).toEqual([{ date: "2026-03-15", mood: 7 }]);
  });
});

describe("Cell formatting", () => {
  function formatCell(value) {
    if (value == null) return "";
    if (value instanceof Date) return value.toISOString().slice(0, 10);
    if (typeof value === "bigint") return value.toString();
    return String(value);
  }

  it("formats null as empty", () => { expect(formatCell(null)).toBe(""); });
  it("formats numbers", () => { expect(formatCell(42)).toBe("42"); });
  it("formats bigint", () => { expect(formatCell(42n)).toBe("42"); });
  it("formats dates", () => { expect(formatCell(new Date("2026-03-15T00:00:00Z"))).toBe("2026-03-15"); });
});
