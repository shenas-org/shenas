import { LitElement, html, css } from "lit";
import type { TemplateResult, CSSResult } from "lit";

interface BlockerRow {
  root_identifier: string | null;
  root_title: string | null;
  node_identifier: string | null;
  node_title: string | null;
  max_chain_depth: number;
  chain_path: string | null;
}

export class BlockerTable extends LitElement {
  static properties = {
    rows: { type: Array },
  };

  declare rows: BlockerRow[];

  static styles: CSSResult = css`
    :host {
      display: block;
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 16px;
    }
    h3 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th {
      text-align: left;
      color: #888;
      font-weight: 500;
      padding: 6px 8px;
      border-bottom: 1px solid #f0f0f0;
    }
    td {
      padding: 6px 8px;
      border-bottom: 1px solid #f8f8f8;
      color: #333;
      vertical-align: top;
    }
    .depth-badge {
      display: inline-block;
      background: #e74c3c;
      color: #fff;
      border-radius: 10px;
      padding: 1px 7px;
      font-size: 11px;
      font-weight: 600;
    }
    .depth-1 {
      background: #f39c12;
    }
    .depth-2 {
      background: #e67e22;
    }
    .depth-badge.depth-3,
    .depth-badge.depth-4,
    .depth-badge.depth-5 {
      background: #e74c3c;
    }
    .identifier {
      font-family: monospace;
      color: #6b5ce7;
      font-size: 11px;
    }
    .title {
      color: #444;
    }
    .chain-path {
      color: #aaa;
      font-size: 11px;
      font-family: monospace;
    }
    .no-data {
      color: #999;
      font-size: 13px;
      padding: 24px 0;
      text-align: center;
    }
  `;

  constructor() {
    super();
    this.rows = [];
  }

  render(): TemplateResult {
    if (this.rows.length === 0) {
      return html`
        <h3>Top 10 Deepest Blocker Chains</h3>
        <div class="no-data">No blocker chains — all clear.</div>
      `;
    }

    return html`
      <h3>Top 10 Deepest Blocker Chains</h3>
      <table>
        <thead>
          <tr>
            <th>Depth</th>
            <th>Blocked issue</th>
            <th>Root bottleneck</th>
            <th>Chain path</th>
          </tr>
        </thead>
        <tbody>
          ${this.rows.map(
            (row) => html`
              <tr>
                <td>
                  <span class="depth-badge depth-${row.max_chain_depth}">${row.max_chain_depth}</span>
                </td>
                <td>
                  <span class="identifier">${row.root_identifier ?? "—"}</span><br />
                  <span class="title">${row.root_title ?? ""}</span>
                </td>
                <td>
                  <span class="identifier">${row.node_identifier ?? "—"}</span><br />
                  <span class="title">${row.node_title ?? ""}</span>
                </td>
                <td><span class="chain-path">${row.chain_path ?? "—"}</span></td>
              </tr>
            `,
          )}
        </tbody>
      </table>
    `;
  }
}

customElements.define("blocker-table", BlockerTable);
