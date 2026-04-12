import { LitElement, html, css, nothing } from "lit";
import { gql, gqlFull, renderMessage, buttonStyles, formStyles, messageStyles, tableStyles } from "shenas-frontends";

interface Column {
  name: string;
  dbType: string;
  nullable: boolean;
  description: string;
  unit: string | null;
}

interface DataResource {
  id: string;
  schemaName: string;
  tableName: string;
  displayName: string;
  description: string;
  pluginKind: string;
  pluginName: string;
  kind: string | null;
  queryHint: string | null;
  asOfMacro: string | null;
  primaryKey: string[];
  columns: Column[];
  timeColumns: { timeAt: string | null; timeStart: string | null; timeEnd: string | null };
  freshness: { lastRefreshed: string | null; slaMinutes: number | null; isStale: boolean };
  quality: {
    expectedRowCountMin: number | null;
    expectedRowCountMax: number | null;
    actualRowCount: number | null;
    latestChecks: Array<{ checkType: string; status: string; message: string; checkedAt: string }>;
  };
  userNotes: string;
  tags: string[];
  upstream: Array<{ id: string; displayName: string; kind: string | null }> | null;
  downstream: Array<{ id: string; displayName: string; kind: string | null }> | null;
}

interface Message {
  type: string;
  text: string;
}

const FIELDS = `
  id schemaName tableName displayName description pluginKind pluginName
  kind queryHint asOfMacro primaryKey
  columns { name dbType nullable description unit }
  timeColumns { timeAt timeStart timeEnd }
  freshness { lastRefreshed slaMinutes isStale }
  quality { expectedRowCountMin expectedRowCountMax actualRowCount
    latestChecks { checkType status message checkedAt } }
  userNotes tags
`;

const DETAIL_FIELDS = `${FIELDS}
  upstream { id displayName kind }
  downstream { id displayName kind }
`;

class CatalogPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _resources: { state: true },
    _loading: { state: true },
    _expanded: { state: true },
    _detail: { state: true },
    _message: { state: true },
    _search: { state: true },
    _filterKind: { state: true },
    _editNotes: { state: true },
    _editTags: { state: true },
    _editSla: { state: true },
    _editRowMin: { state: true },
    _editRowMax: { state: true },
  };

  static styles = [
    tableStyles,
    buttonStyles,
    formStyles,
    messageStyles,
    css`
      :host {
        display: block;
      }
      .search-bar {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        align-items: center;
      }
      .search-bar input {
        flex: 1;
        padding: 0.4rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
      }
      .search-bar select {
        padding: 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
      }
      .detail-panel {
        margin: 0.5rem 0 1rem;
        padding: 1rem;
        border: 1px solid var(--shenas-border, #e0e0e0);
        border-radius: 8px;
        background: var(--shenas-bg-secondary, #fafafa);
      }
      .detail-panel h3 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
      }
      .detail-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        margin-bottom: 0.8rem;
      }
      .detail-grid label {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        font-size: 0.85rem;
      }
      .detail-full {
        grid-column: 1 / -1;
      }
      .badge {
        display: inline-block;
        font-size: 0.7rem;
        padding: 1px 6px;
        border-radius: 3px;
        background: var(--shenas-border-light, #f0f0f0);
        color: var(--shenas-text-muted, #888);
        margin-left: 4px;
      }
      .dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 4px;
        vertical-align: middle;
      }
      .dot-green {
        background: #4caf50;
      }
      .dot-yellow {
        background: #ff9800;
      }
      .dot-red {
        background: #c62828;
      }
      .dot-gray {
        background: #bbb;
      }
      .col-table {
        width: 100%;
        font-size: 0.8rem;
        border-collapse: collapse;
        margin: 0.5rem 0;
      }
      .col-table th,
      .col-table td {
        text-align: left;
        padding: 0.3rem 0.5rem;
        border-bottom: 1px solid var(--shenas-border-light, #eee);
      }
      .col-table th {
        font-weight: 600;
        color: var(--shenas-text-secondary, #666);
      }
      .lineage-list {
        font-size: 0.85rem;
      }
      .lineage-list a {
        color: var(--shenas-text, #222);
        cursor: pointer;
        text-decoration: none;
      }
      .lineage-list a:hover {
        text-decoration: underline;
      }
      .section-label {
        font-weight: 600;
        font-size: 0.85rem;
        margin: 0.8rem 0 0.3rem;
        color: var(--shenas-text-secondary, #666);
      }
      .actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.8rem;
      }
      textarea {
        width: 100%;
        min-height: 60px;
        font-size: 0.85rem;
        padding: 0.4rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        resize: vertical;
        box-sizing: border-box;
      }
      .muted {
        color: var(--shenas-text-muted, #888);
        font-size: 0.8rem;
      }
      .mono {
        font-family: monospace;
      }
    `,
  ];

  declare apiBase: string;
  declare _resources: DataResource[];
  declare _loading: boolean;
  declare _expanded: string | null;
  declare _detail: DataResource | null;
  declare _message: Message | null;
  declare _search: string;
  declare _filterKind: string;
  declare _editNotes: string;
  declare _editTags: string;
  declare _editSla: string;
  declare _editRowMin: string;
  declare _editRowMax: string;

  constructor() {
    super();
    this.apiBase = "/api";
    this._resources = [];
    this._loading = true;
    this._expanded = null;
    this._detail = null;
    this._message = null;
    this._search = "";
    this._filterKind = "";
    this._editNotes = "";
    this._editTags = "";
    this._editSla = "";
    this._editRowMin = "";
    this._editRowMax = "";
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._fetchAll();
  }

  async _fetchAll(): Promise<void> {
    this._loading = true;
    const data = await gql(this.apiBase, `{ dataResources { ${FIELDS} } }`);
    this._resources = (data?.dataResources as DataResource[]) || [];
    this._loading = false;
  }

  async _expand(id: string): Promise<void> {
    if (this._expanded === id) {
      this._expanded = null;
      this._detail = null;
      return;
    }
    this._expanded = id;
    const data = await gql(this.apiBase, `query($id: String!) { dataResource(resourceId: $id) { ${DETAIL_FIELDS} } }`, {
      id,
    });
    this._detail = (data?.dataResource as DataResource) || null;
    if (this._detail) {
      this._editNotes = this._detail.userNotes || "";
      this._editTags = this._detail.tags.join(", ");
      this._editSla = this._detail.freshness.slaMinutes?.toString() || "";
      this._editRowMin = this._detail.quality.expectedRowCountMin?.toString() || "";
      this._editRowMax = this._detail.quality.expectedRowCountMax?.toString() || "";
      // Show detail in the app-shell right panel
      this.dispatchEvent(
        new CustomEvent("show-resource", {
          bubbles: true,
          composed: true,
          detail: this._detail,
        }),
      );
    }
  }

  async _saveAnnotation(): Promise<void> {
    if (!this._expanded) return;
    await gqlFull(
      this.apiBase,
      `mutation($id: String!, $ann: DataResourceAnnotationInput!) {
        updateDataResource(resourceId: $id, annotation: $ann) { id }
      }`,
      {
        id: this._expanded,
        ann: {
          userNotes: this._editNotes,
          tags: this._editTags,
          freshnessSlaMinutes: this._editSla ? parseInt(this._editSla) : null,
          expectedRowCountMin: this._editRowMin ? parseInt(this._editRowMin) : null,
          expectedRowCountMax: this._editRowMax ? parseInt(this._editRowMax) : null,
        },
      },
    );
    this._message = { type: "success", text: "Saved" };
    await this._fetchAll();
    await this._expand(this._expanded);
  }

  async _runChecks(): Promise<void> {
    if (!this._expanded) return;
    await gqlFull(
      this.apiBase,
      `mutation($id: String) { runQualityChecks(resourceId: $id) { checkType status message } }`,
      { id: this._expanded },
    );
    this._message = { type: "success", text: "Quality checks complete" };
    await this._expand(this._expanded);
  }

  _navigateToPlugin(kind: string, name: string): void {
    this.dispatchEvent(
      new CustomEvent("navigate", {
        bubbles: true,
        composed: true,
        detail: { path: `/settings/${kind}/${name}`, label: name },
      }),
    );
  }

  _formatRows(n: number | null): string {
    if (n === null || n === undefined) return "--";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return `${n}`;
  }

  _freshnessDot(r: DataResource): unknown {
    if (!r.freshness.lastRefreshed) return html`<span class="dot dot-gray"></span>`;
    if (r.freshness.isStale) return html`<span class="dot dot-red"></span>`;
    return html`<span class="dot dot-green"></span>`;
  }

  _filtered(): DataResource[] {
    let list = this._resources;
    if (this._search) {
      const q = this._search.toLowerCase();
      list = list.filter(
        (r) =>
          r.id.toLowerCase().includes(q) ||
          r.displayName.toLowerCase().includes(q) ||
          r.description.toLowerCase().includes(q),
      );
    }
    if (this._filterKind) {
      list = list.filter((r) => r.kind === this._filterKind);
    }
    return list;
  }

  render() {
    if (this._loading) return html``;
    const kinds = [...new Set(this._resources.map((r) => r.kind).filter(Boolean))].sort();
    const filtered = this._filtered();
    return html`
      <div>
        ${renderMessage(this._message)}
        <div class="search-bar">
          <input
            type="text"
            placeholder="Search resources..."
            .value=${this._search}
            @input=${(e: InputEvent) => {
              this._search = (e.target as HTMLInputElement).value;
            }}
          />
          <select
            .value=${this._filterKind}
            @change=${(e: Event) => {
              this._filterKind = (e.target as HTMLSelectElement).value;
            }}
          >
            <option value="">All kinds</option>
            ${kinds.map((k) => html`<option value=${k!}>${k}</option>`)}
          </select>
        </div>
        <shenas-data-list
          .columns=${[
            {
              label: "Name",
              render: (r: DataResource) =>
                html`<a
                    @click=${() => this._expand(r.id)}
                    style="cursor:pointer;text-decoration:underline;color:inherit"
                    >${r.displayName}</a
                  >
                  <span class="badge">${r.kind || "table"}</span>`,
            },
            {
              label: "Plugin",
              class: "mono",
              render: (r: DataResource) =>
                html`<a
                  @click=${() => this._navigateToPlugin(r.pluginKind, r.pluginName)}
                  style="cursor:pointer;text-decoration:underline;color:inherit"
                  >${r.pluginName}</a
                >`,
            },
            {
              label: "Rows",
              render: (r: DataResource) => html`${this._formatRows(r.quality.actualRowCount)}`,
            },
            {
              label: "Freshness",
              render: (r: DataResource) =>
                html`${this._freshnessDot(r)}${r.freshness.lastRefreshed
                  ? r.freshness.lastRefreshed.slice(0, 16).replace("T", " ")
                  : "never"}`,
            },
          ]}
          .rows=${filtered}
          empty-text="No data resources found"
        ></shenas-data-list>
      </div>
    `;
  }

  _renderDetail(r: DataResource) {
    return html`
      <div class="detail-panel">
        <h3>${r.displayName} <span class="badge">${r.kind || "table"}</span> <span class="muted">${r.id}</span></h3>
        <p class="muted">${r.description}</p>

        <div class="section-label">Columns</div>
        <table class="col-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Description</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            ${r.columns.map(
              (c) => html`
                <tr>
                  <td class="mono">${c.name}${r.primaryKey.includes(c.name) ? " *" : ""}</td>
                  <td class="mono">${c.dbType}</td>
                  <td>${c.description}</td>
                  <td>${c.unit || ""}</td>
                </tr>
              `,
            )}
          </tbody>
        </table>

        ${r.upstream?.length || r.downstream?.length
          ? html`
              <div class="section-label">Lineage</div>
              <div class="lineage-list">
                ${r.upstream?.length
                  ? html`<strong>Upstream:</strong>
                      ${r.upstream.map((u) => html` <a @click=${() => this._expand(u.id)}>${u.id}</a>`)} `
                  : nothing}
                ${r.downstream?.length
                  ? html`<strong>Downstream:</strong>
                      ${r.downstream.map((d) => html` <a @click=${() => this._expand(d.id)}>${d.id}</a>`)} `
                  : nothing}
              </div>
            `
          : nothing}

        <div class="section-label">Freshness & Quality</div>
        <div class="detail-grid">
          <label>
            Freshness SLA (minutes)
            <input
              type="number"
              .value=${this._editSla}
              @input=${(e: InputEvent) => {
                this._editSla = (e.target as HTMLInputElement).value;
              }}
            />
          </label>
          <label>
            Row count range
            <div style="display:flex;gap:0.3rem;align-items:center">
              <input
                type="number"
                placeholder="min"
                .value=${this._editRowMin}
                style="width:80px"
                @input=${(e: InputEvent) => {
                  this._editRowMin = (e.target as HTMLInputElement).value;
                }}
              />
              --
              <input
                type="number"
                placeholder="max"
                .value=${this._editRowMax}
                style="width:80px"
                @input=${(e: InputEvent) => {
                  this._editRowMax = (e.target as HTMLInputElement).value;
                }}
              />
              <span class="muted">(actual: ${this._formatRows(r.quality.actualRowCount)})</span>
            </div>
          </label>
        </div>

        ${r.quality.latestChecks.length
          ? html`
              <div class="section-label">Latest Checks</div>
              ${r.quality.latestChecks.map(
                (c) => html`
                  <div>
                    <span
                      class="dot ${c.status === "pass" ? "dot-green" : c.status === "warn" ? "dot-yellow" : "dot-red"}"
                    ></span>
                    ${c.checkType}: ${c.message}
                    <span class="muted">${c.checkedAt.slice(0, 16)}</span>
                  </div>
                `,
              )}
            `
          : nothing}

        <div class="section-label">Notes</div>
        <textarea
          .value=${this._editNotes}
          placeholder="Add notes..."
          @input=${(e: InputEvent) => {
            this._editNotes = (e.target as HTMLTextAreaElement).value;
          }}
        ></textarea>

        <div class="detail-grid">
          <label class="detail-full">
            Tags (comma-separated)
            <input
              .value=${this._editTags}
              @input=${(e: InputEvent) => {
                this._editTags = (e.target as HTMLInputElement).value;
              }}
            />
          </label>
        </div>

        <div class="actions">
          <button @click=${this._saveAnnotation}>Save</button>
          <button @click=${this._runChecks}>Run Checks</button>
          <button
            @click=${() => {
              this._expanded = null;
              this._detail = null;
            }}
          >
            Close
          </button>
        </div>
      </div>
    `;
  }
}

customElements.define("shenas-catalog", CatalogPage);
