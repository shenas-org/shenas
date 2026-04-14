import { html } from "lit";
import type { TemplateResult } from "lit";

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
}

export interface ApiFetchFullResult<T = unknown> {
  ok: boolean;
  status: number;
  data: T | null;
}

export interface MessageBanner {
  type: string;
  text: string;
}

export interface CommandDescriptor {
  id: string;
  label: string;
  category: string;
  description?: string;
  [key: string]: unknown;
}

/**
 * Shared API fetch wrapper. Returns parsed JSON on success, null on error.
 * For non-GET requests, pass method and optional json body.
 */
export async function apiFetch<T = unknown>(
  apiBase: string,
  path: string,
  options: ApiFetchOptions = {},
): Promise<T | null> {
  const { method = "GET", json, ...rest } = options;
  const fetchOptions: RequestInit = { method, ...rest };
  if (json !== undefined) {
    fetchOptions.headers = { "Content-Type": "application/json", ...(rest.headers ?? {}) };
    fetchOptions.body = JSON.stringify(json);
  }
  const resp = await fetch(`${apiBase}${path}`, fetchOptions);
  if (!resp.ok) {
    console.warn(`apiFetch ${method} ${path} failed: ${resp.status}`);
    return null;
  }
  return resp.json() as Promise<T>;
}

/**
 * Like apiFetch but returns { ok, data, status } so callers can distinguish
 * errors and access the response body on failure.
 */
export async function apiFetchFull<T = unknown>(
  apiBase: string,
  path: string,
  options: ApiFetchOptions = {},
): Promise<ApiFetchFullResult<T>> {
  const { method = "GET", json, ...rest } = options;
  const fetchOptions: RequestInit = { method, ...rest };
  if (json !== undefined) {
    fetchOptions.headers = { "Content-Type": "application/json", ...(rest.headers ?? {}) };
    fetchOptions.body = JSON.stringify(json);
  }
  const resp = await fetch(`${apiBase}${path}`, fetchOptions);
  const data = await resp.json().catch(() => null);
  return { ok: resp.ok, status: resp.status, data: data as T | null };
}

/**
 * Query DuckDB via Arrow IPC and return rows as an array of plain objects.
 * Uses the REST /api/query endpoint (binary Arrow stream, not GraphQL).
 */
export async function arrowQuery(apiBase: string, sql: string): Promise<Record<string, unknown>[] | null> {
  const arrowUrl = "/vendor/apache-arrow.js";
  const mod = (await import(/* @vite-ignore */ arrowUrl)) as {
    tableFromIPC: (buf: Uint8Array) => Promise<{ toArray: () => { toJSON: () => Record<string, unknown> }[] }>;
  };
  const resp = await fetch(`${apiBase}/query?sql=${encodeURIComponent(sql)}`);
  if (!resp.ok) return null;
  const buf = await resp.arrayBuffer();
  const table = await mod.tableFromIPC(new Uint8Array(buf));
  return table.toArray().map((row) => row.toJSON());
}

/**
 * Render a message banner. Pass a { type, text } object or null.
 */
export function renderMessage(message: MessageBanner | null | undefined): TemplateResult | string {
  if (!message) return "";
  return html`<div class="message ${message.type}">${message.text}</div>`;
}

/**
 * Dispatch a register-command event from an element.
 * The app-shell listens for these to populate the command palette.
 */
export function registerCommands(element: HTMLElement, componentId: string, commands: CommandDescriptor[]): void {
  element.dispatchEvent(
    new CustomEvent("register-command", {
      bubbles: true,
      composed: true,
      detail: { componentId, commands },
    }),
  );
}

/**
 * Open an external URL. In Tauri (desktop) this delegates to the OS browser
 * via the shell plugin's `open` command. In a regular web browser it opens
 * a new tab. In both cases the current app/window stays put.
 */
export function openExternal(url: string): void {
  const tauri = (
    window as unknown as {
      __TAURI_INTERNALS__?: { invoke: (cmd: string, args: unknown) => Promise<unknown> };
    }
  ).__TAURI_INTERNALS__;
  if (tauri && typeof tauri.invoke === "function") {
    tauri.invoke("plugin:shell|open", { path: url }).catch(() => window.open(url, "_blank", "noopener"));
  } else {
    window.open(url, "_blank", "noopener");
  }
}
