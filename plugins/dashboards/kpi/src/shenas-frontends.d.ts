declare module "shenas-frontends" {
  export interface RowData {
    [key: string]: unknown;
  }
  export interface Table {
    schema: { fields: Array<{ name: string }> };
    batches: unknown[];
    numRows: number;
    getChild(name: string): { get(i: number): unknown; toArray(): ArrayLike<unknown> } | null;
  }
  export function query(base: string, sql: string): Promise<Table>;
  export function arrowToRows(table: Table): RowData[];
  export function arrowToColumns(table: Table): Record<string, ArrayLike<unknown>>;
  export function arrowDatesToUnix(arr: ArrayLike<unknown>): Float64Array;
}
