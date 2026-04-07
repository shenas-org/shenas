import { tableFromIPC } from "apache-arrow";
import type { Table } from "apache-arrow";

export interface RowData {
  [key: string]: unknown;
}

export async function query(apiBase: string, sql: string): Promise<Table> {
  const res = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  const buf = await res.arrayBuffer();
  return await tableFromIPC(buf);
}

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
