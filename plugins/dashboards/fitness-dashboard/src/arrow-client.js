import { tableFromIPC } from "apache-arrow";

export async function query(apiBase, sql) {
  const res = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  const buf = await res.arrayBuffer();
  return await tableFromIPC(buf);
}

export function arrowToColumns(table) {
  const result = {};
  for (const field of table.schema.fields) {
    const col = table.getChild(field.name);
    result[field.name] = col.toArray();
  }
  return result;
}

export function arrowDatesToUnix(arr) {
  return Float64Array.from(arr, (v) => {
    if (v == null) return null;
    // Arrow JS date32/date64 returns milliseconds since epoch
    const n = typeof v === "bigint" ? Number(v) : Number(v);
    if (Number.isNaN(n)) return null;
    // If value > 1e9 it's already ms; if small it's days since epoch
    return n > 1e9 ? n / 1000 : n * 86400;
  });
}
