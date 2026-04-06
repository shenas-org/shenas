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

export function arrowToRows(table) {
  const fields = table.schema.fields.map((f) => f.name);
  const rows = [];
  for (let i = 0; i < table.numRows; i++) {
    const row = {};
    for (const name of fields) {
      row[name] = table.getChild(name).get(i);
    }
    rows.push(row);
  }
  return rows;
}
