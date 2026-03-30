import { html } from "lit";

function _buildFetchOptions(options) {
  const { method = "GET", json, ...rest } = options;
  const fetchOptions = { method, ...rest };
  if (json !== undefined) {
    fetchOptions.headers = { "Content-Type": "application/json", ...rest.headers };
    fetchOptions.body = JSON.stringify(json);
  }
  return fetchOptions;
}

/**
 * Shared API fetch wrapper. Returns parsed JSON on success, null on error.
 * For non-GET requests, pass method and optional json body.
 */
export async function apiFetch(apiBase, path, options = {}) {
  const result = await apiFetchFull(apiBase, path, options);
  return result.ok ? result.data : null;
}

/**
 * Like apiFetch but returns { ok, data, status } so callers can distinguish
 * errors and access the response body on failure.
 */
export async function apiFetchFull(apiBase, path, options = {}) {
  const fetchOptions = _buildFetchOptions(options);
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
