import { tableFromIPC } from "apache-arrow";

function getApiToken() {
  const meta = document.querySelector('meta[name="shenas-api-token"]');
  return meta ? meta.getAttribute("content") : "";
}

function authHeaders() {
  const token = getApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function query(apiBase, sql) {
  const res = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  const buf = await res.arrayBuffer();
  return tableFromIPC(buf);
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
    const ms = typeof v === "number" ? v * 86400000 : new Date(v).getTime();
    return ms / 1000;
  });
}
