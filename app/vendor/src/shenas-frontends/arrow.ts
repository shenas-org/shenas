/**
 * Shared Arrow IPC query helpers for dashboards.
 *
 * Consolidates the duplicated arrow-client.ts files from individual
 * dashboard plugins into a single reusable module.
 */

import { tableFromIPC } from "apache-arrow";
import type { Table } from "apache-arrow";

export type { Table } from "apache-arrow";

export interface RowData {
  [key: string]: unknown;
}

/** Execute a SQL query via the /query endpoint and return an Arrow Table. */
export async function query(apiBase: string, sql: string): Promise<Table> {
  const res = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  const buf = await res.arrayBuffer();
  return await tableFromIPC(buf);
}

/** Convert an Arrow Table to an array of plain row objects. */
export function arrowToRows(table: Table): RowData[] {
  const fields = table.schema.fields.map((f) => f.name);
  const rows: RowData[] = [];
  for (let i = 0; i < table.numRows; i++) {
    const row: RowData = {};
    for (const name of fields) {
      row[name] = table.getChild(name)!.get(i);
    }
    rows.push(row);
  }
  return rows;
}

/** Convert an Arrow Table to a column-oriented record of typed arrays. */
export function arrowToColumns(table: Table): Record<string, ArrayLike<unknown>> {
  const result: Record<string, ArrayLike<unknown>> = {};
  for (const field of table.schema.fields) {
    const col = table.getChild(field.name);
    result[field.name] = col!.toArray();
  }
  return result;
}

/** Convert Arrow date/timestamp arrays to Unix epoch seconds (Float64Array). */
export function arrowDatesToUnix(arr: ArrayLike<unknown>): Float64Array {
  return Float64Array.from(arr as ArrayLike<number>, (v: unknown) => {
    if (v == null) return null as unknown as number;
    const n = typeof v === "bigint" ? Number(v) : Number(v);
    if (Number.isNaN(n)) return null as unknown as number;
    // If value > 1e9 it's already ms; if small it's days since epoch
    return n > 1e9 ? n / 1000 : n * 86400;
  });
}
