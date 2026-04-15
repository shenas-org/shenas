declare module "shenas-frontends" {
  export interface RowData {
    [key: string]: unknown;
  }
  export interface Table {
    schema: { fields: Array<{ name: string }> };
    batches: unknown[];
  }
  export function query(base: string, sql: string): Promise<Table>;
  export function arrowToRows(table: Table): RowData[];
  export function arrowToColumns(table: Table): Record<string, ArrayLike<unknown>>;
  export function arrowDatesToUnix(arr: ArrayLike<unknown>): Float64Array;

  // Apollo Client access -- re-exported from the real vendor module.
  // Minimal shape of the ApolloClient instance we actually call in
  // shared components; the real Apollo type is richer but we only need
  // `query` to be callable here.
  export interface ApolloClientLike {
    query<T = Record<string, unknown>>(options: {
      query: unknown;
      variables?: Record<string, unknown>;
      fetchPolicy?: string;
    }): Promise<{ data?: T | null }>;
  }
  export function getClient(): ApolloClientLike;

  // `gqlTag` is Apollo's template literal tag (re-exported under this
  // name to avoid colliding with the legacy `gql()` fetch helper that
  // used to live here).
  export function gqlTag(strings: TemplateStringsArray, ...values: unknown[]): unknown;
}
