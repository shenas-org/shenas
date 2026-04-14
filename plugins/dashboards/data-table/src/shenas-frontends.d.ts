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
  export function gql(
    base: string,
    query: string,
    variables?: Record<string, unknown>,
  ): Promise<Record<string, unknown> | null>;
  export function getClient(apiBase?: string): {
    query(opts: { query: unknown; variables?: Record<string, unknown>; fetchPolicy?: string }): Promise<{
      data: Record<string, unknown>;
    }>;
  };
  export function gqlTag(strings: TemplateStringsArray, ...values: unknown[]): unknown;
}
