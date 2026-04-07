import { tableFromIPC } from "apache-arrow";
import type { Table } from "apache-arrow";

export async function query(apiBase: string, sql: string): Promise<Table> {
  const res = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  const buf = await res.arrayBuffer();
  return await tableFromIPC(buf);
}

export function arrowToColumns(table: Table): Record<string, ArrayLike<unknown>> {
  const result: Record<string, ArrayLike<unknown>> = {};
  for (const field of table.schema.fields) {
    const col = table.getChild(field.name);
    result[field.name] = col!.toArray();
  }
  return result;
}

export function arrowDatesToUnix(arr: ArrayLike<unknown>): Float64Array {
  return Float64Array.from(arr as ArrayLike<number>, (v: unknown) => {
    if (v == null) return null as unknown as number;
    // Arrow JS date32/date64 returns milliseconds since epoch
    const n = typeof v === "bigint" ? Number(v) : Number(v);
    if (Number.isNaN(n)) return null as unknown as number;
    // If value > 1e9 it's already ms; if small it's days since epoch
    return n > 1e9 ? n / 1000 : n * 86400;
  });
}
