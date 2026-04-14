declare module "shenas-frontends" {
  // Apollo Client
  import type { ApolloClient, DocumentNode } from "@apollo/client/core";
  import type { ReactiveController, ReactiveControllerHost } from "lit";

  export function getClient(apiBase?: string): ApolloClient<unknown>;
  export function gqlTag(strings: TemplateStringsArray, ...values: unknown[]): DocumentNode;

  interface ApolloControllerOptions {
    client?: ApolloClient<unknown>;
    variables?: Record<string, unknown>;
    fetchPolicy?: string;
    noAutoSubscribe?: boolean;
    [key: string]: unknown;
  }

  interface MutateParams {
    variables?: Record<string, unknown>;
    refetchQueries?: Array<{ query: DocumentNode; variables?: Record<string, unknown> }>;
    [key: string]: unknown;
  }

  export class ApolloQueryController<TData = Record<string, unknown>> implements ReactiveController {
    constructor(host: ReactiveControllerHost, query: DocumentNode, options?: ApolloControllerOptions);
    data: TData | null;
    loading: boolean;
    error: Error | null;
    client: ApolloClient<unknown> | null;
    subscribe(options?: ApolloControllerOptions): void;
    refetch(variables?: Record<string, unknown>): Promise<{ data: TData }>;
    hostConnected(): void;
    hostDisconnected(): void;
  }

  export class ApolloMutationController<TData = Record<string, unknown>> implements ReactiveController {
    constructor(host: ReactiveControllerHost, mutation: DocumentNode, options?: ApolloControllerOptions);
    data: TData | null;
    loading: boolean;
    error: Error | null;
    called: boolean;
    client: ApolloClient<unknown> | null;
    mutate(params?: MutateParams): Promise<{ data?: TData | null }>;
    hostConnected(): void;
    hostDisconnected(): void;
  }

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
  export interface RowData {
    [key: string]: unknown;
  }
  export interface Table {
    schema: { fields: Array<{ name: string }> };
    batches: unknown[];
  }
  export function query(base: string, sql: string): Promise<Table>;
  export function arrowToRows(table: Table): RowData[];
  export function arrowQuery(base: string, sql: string): Promise<unknown>;
  export function renderMessage(msg: unknown): import("lit").TemplateResult | string;
  export function registerCommands<T>(host: HTMLElement, componentId: string, commands: T[]): void;
  export function openExternal(url: string): void;
  export function sortActions<T>(actions: T[], bindings?: Record<string, string>): T[];
  export function parseHotkey(binding: string): Record<string, unknown>;
  export function formatHotkey(event: KeyboardEvent): string;
  export function matchesHotkey(event: KeyboardEvent, binding: string): boolean;
  export interface MessageBanner {
    type: string;
    text: string;
  }
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
