import { describe, it, expect } from "vitest";
import { tableFromArrays } from "apache-arrow";
import { arrowToColumns, arrowDatesToUnix } from "../arrow-client.ts";

describe("arrowToColumns", () => {
  it("converts arrow table to column dict", () => {
    const table = tableFromArrays({
      date: ["2026-03-15", "2026-03-16"],
      rmssd: new Float64Array([42.0, 45.0]),
    });
    const cols = arrowToColumns(table);
    expect(Object.keys(cols)).toEqual(["date", "rmssd"]);
    expect(cols.rmssd[0]).toBe(42.0);
    expect(cols.rmssd[1]).toBe(45.0);
  });

  it("handles empty table", () => {
    const table = tableFromArrays({
      id: new Int32Array([]),
    });
    const cols = arrowToColumns(table);
    expect(cols.id.length).toBe(0);
  });
});

describe("arrowDatesToUnix", () => {
  it("converts day numbers to unix timestamps", () => {
    // Day 0 = 1970-01-01, day 1 = 86400 seconds
    const result = arrowDatesToUnix([1]);
    expect(result[0]).toBe(86400);
  });

  it("converts multiple day numbers", () => {
    const result = arrowDatesToUnix([0, 1]);
    expect(result[0]).toBe(0);
    expect(result[1]).toBe(86400);
  });
});
