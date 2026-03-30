import { html } from "lit";

/**
 * Shared API fetch wrapper. Returns parsed JSON on success, null on error.
 * For non-GET requests, pass method and optional json body.
 */
export async function apiFetch(apiBase, path, options = {}) {
  const { method = "GET", json, ...rest } = options;
  const fetchOptions = { method, ...rest };
  if (json !== undefined) {
    fetchOptions.headers = { "Content-Type": "application/json", ...rest.headers };
    fetchOptions.body = JSON.stringify(json);
  }
  const resp = await fetch(`${apiBase}${path}`, fetchOptions);
  if (!resp.ok) return null;
  return resp.json();
}

/**
 * Like apiFetch but returns { ok, data, status } so callers can distinguish
 * errors and access the response body on failure.
 */
export async function apiFetchFull(apiBase, path, options = {}) {
  const { method = "GET", json, ...rest } = options;
  const fetchOptions = { method, ...rest };
  if (json !== undefined) {
    fetchOptions.headers = { "Content-Type": "application/json", ...rest.headers };
    fetchOptions.body = JSON.stringify(json);
  }
  const resp = await fetch(`${apiBase}${path}`, fetchOptions);
  const data = await resp.json().catch(() => null);
  return { ok: resp.ok, status: resp.status, data };
}

/**
 * Render a message banner. Pass a { type, text } object or null.
 */
export function renderMessage(message) {
  if (!message) return "";
  return html`<div class="message ${message.type}">${message.text}</div>`;
}
