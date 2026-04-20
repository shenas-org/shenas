import { describe, it, expect } from "vitest";
import { arrowToRows, arrowToColumns, arrowDatesToUnix } from "../shenas-frontends/arrow.ts";
import type { Table } from "apache-arrow";

/** Build a minimal Arrow-Table-like stub for testing conversion helpers. */
function stubTable(columns: Record<string, unknown[]>): Table {
  const fieldNames = Object.keys(columns);
  const numRows = columns[fieldNames[0]]?.length ?? 0;
  return {
    schema: { fields: fieldNames.map((name) => ({ name })) },
    numRows,
    getChild(name: string) {
      const data = columns[name] ?? [];
      return {
        get(index: number) {
          return data[index];
        },
        toArray() {
          return data;
        },
      };
    },
  } as unknown as Table;
}

describe("arrowToRows", () => {
  it("converts a table with rows to an array of objects", () => {
    const table = stubTable({ name: ["Alice", "Bob"], age: [30, 25] });
    const rows = arrowToRows(table);
    expect(rows).toEqual([
      { name: "Alice", age: 30 },
      { name: "Bob", age: 25 },
    ]);
  });

  it("returns empty array for zero-row table", () => {
    const table = stubTable({ name: [] });
    expect(arrowToRows(table)).toEqual([]);
  });

  it("preserves null values", () => {
    const table = stubTable({ value: [1, null, 3] });
    const rows = arrowToRows(table);
    expect(rows[1]!.value).toBeNull();
  });
});

describe("arrowToColumns", () => {
  it("converts a table to column-oriented arrays", () => {
    const table = stubTable({ x: [1, 2], y: [3, 4] });
    const cols = arrowToColumns(table);
    expect(cols.x).toEqual([1, 2]);
    expect(cols.y).toEqual([3, 4]);
  });

  it("returns empty arrays for zero-row table", () => {
    const table = stubTable({ x: [] });
    const cols = arrowToColumns(table);
    expect(cols.x).toEqual([]);
  });
});

describe("arrowDatesToUnix", () => {
  it("converts millisecond timestamps to seconds", () => {
    // 2023-01-01T00:00:00Z = 1672531200000 ms
    const ms = 1672531200000;
    const result = arrowDatesToUnix([ms]);
    expect(result[0]).toBeCloseTo(ms / 1000, 3);
  });

  it("converts day-epoch values to seconds", () => {
    // 1 day = 86400 seconds, day-epoch for 1970-01-02
    const result = arrowDatesToUnix([1]);
    expect(result[0]).toBe(86400);
  });

  it("handles null values by coercing to 0 in Float64Array", () => {
    const result = arrowDatesToUnix([null, 1672531200000]);
    // Float64Array cannot store null -- the cast produces 0
    expect(result[0]).toBe(0);
    expect(result[1]).toBeCloseTo(1672531200, 0);
  });

  it("handles bigint values", () => {
    const ms = BigInt(1672531200000);
    const result = arrowDatesToUnix([ms]);
    expect(result[0]).toBeCloseTo(1672531200, 0);
  });

  it("handles NaN values by coercing to 0 in Float64Array", () => {
    const result = arrowDatesToUnix([NaN]);
    // Float64Array.from maps NaN -> callback returns null -> coerced to 0
    expect(result[0]).toBe(0);
  });

  it("handles empty array", () => {
    const result = arrowDatesToUnix([]);
    expect(result.length).toBe(0);
  });

  it("handles small epoch values as day counts", () => {
    // 19358 days from epoch = 2023-01-01 (approx)
    const result = arrowDatesToUnix([19358]);
    expect(result[0]).toBe(19358 * 86400);
  });
});
