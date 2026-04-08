declare module "shenas-frontends" {
  export function gql(
    base: string,
    query: string,
    variables?: Record<string, unknown>,
  ): Promise<Record<string, unknown>>;
  export function gqlFull(
    base: string,
    query: string,
    variables?: Record<string, unknown>,
  ): Promise<{ ok: boolean; data?: Record<string, unknown>; error?: string }>;
  export function apiFetch(
    base: string,
    method: string,
    path: string,
    options?: Record<string, unknown>,
  ): Promise<unknown>;
  export function arrowQuery(base: string, sql: string): Promise<unknown>;
  export function renderMessage(msg: unknown): import("lit").TemplateResult | string;
  export function registerCommands<T>(host: HTMLElement, componentId: string, commands: T[]): void;
  export const PLUGIN_KINDS: Array<{ id: string; label: string }>;
  export function sortActions<T>(actions: T[], bindings?: Record<string, string>): T[];
  export function parseHotkey(binding: string): Record<string, unknown>;
  export function formatHotkey(event: KeyboardEvent): string;
  export function matchesHotkey(event: KeyboardEvent, binding: string): boolean;
  export const buttonStyles: import("lit").CSSResult;
  export const linkStyles: import("lit").CSSResult;
  export const tabStyles: import("lit").CSSResult;
  export const messageStyles: import("lit").CSSResult;
  export const formStyles: import("lit").CSSResult;
  export const cardStyles: import("lit").CSSResult;
  export const tableStyles: import("lit").CSSResult;
  export const codeStyles: import("lit").CSSResult;
  export const utilityStyles: import("lit").CSSResult;
}
