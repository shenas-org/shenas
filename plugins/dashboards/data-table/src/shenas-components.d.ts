declare module "shenas-components" {
  import { LitElement } from "lit";

  interface RowData {
    [key: string]: unknown;
  }

  export class ShenasDataTable extends LitElement {
    _columns: string[];
    _data: RowData[];
    _sortCol: string | null;
    _sortDesc: boolean;
    _page: number;
    get _filteredData(): RowData[];
    get _sortedData(): RowData[];
    get _pagedData(): RowData[];
    _onFilter(col: string, value: string): void;
    _onSort(col: string): void;
  }
}
