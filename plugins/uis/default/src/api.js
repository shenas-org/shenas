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
  if (!resp.ok) {
    console.warn(`apiFetch ${method} ${path} failed: ${resp.status}`);
    return null;
  }
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
 * GraphQL fetch wrapper. Posts a query to /graphql and returns the data object,
 * or null on error. Keeps apiFetch for Arrow IPC and SSE endpoints.
 */
export async function gql(apiBase, query, variables = {}) {
  const resp = await fetch(`${apiBase}/graphql`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  if (!resp.ok) return null;
  const json = await resp.json();
  if (json.errors) {
    console.warn("GraphQL errors:", json.errors);
    return null;
  }
  return json.data;
}

/**
 * Like gql() but returns { ok, data, errors } for mutation result checking.
 */
export async function gqlFull(apiBase, query, variables = {}) {
  const resp = await fetch(`${apiBase}/graphql`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  if (!resp.ok) return { ok: false, data: null, errors: [{ message: `HTTP ${resp.status}` }] };
  const json = await resp.json();
  return { ok: !json.errors, data: json.data, errors: json.errors || [] };
}

/**
 * Render a message banner. Pass a { type, text } object or null.
 */
export function renderMessage(message) {
  if (!message) return "";
  return html`<div class="message ${message.type}">${message.text}</div>`;
}

/**
 * Dispatch a register-command event from an element.
 * The app-shell listens for these to populate the command palette.
 */
export function registerCommands(element, componentId, commands) {
  element.dispatchEvent(new CustomEvent("register-command", {
    bubbles: true,
    composed: true,
    detail: { componentId, commands },
  }));
}
