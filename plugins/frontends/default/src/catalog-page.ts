import { LitElement, html, css, nothing } from "lit";
import {
  ApolloQueryController,
  ApolloMutationController,
  getClient,
  renderMessage,
  buttonStyles,
  formStyles,
  messageStyles,
  tableStyles,
} from "shenas-frontends";
import { GET_DATA_RESOURCES, GET_DATA_RESOURCE_DETAIL } from "./graphql/queries.ts";
import { UPDATE_DATA_RESOURCE, RUN_QUALITY_CHECKS } from "./graphql/mutations.ts";

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
  plugin: { name: string; displayName: string };
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
  upstreamTransforms: Array<{
    id: number;
    transformType: string;
    source: { id: string; displayName: string };
    description: string;
  }> | null;
  downstreamTransforms: Array<{
    id: number;
    transformType: string;
    target: { id: string; displayName: string };
    description: string;
  }> | null;
}

interface Message {
  type: string;
  text: string;
}

class CatalogPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
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

  private _client = getClient();

  private _resourcesQuery = new ApolloQueryController(this, GET_DATA_RESOURCES, {
    client: this._client,
  });

  private _updateMutation = new ApolloMutationController(this, UPDATE_DATA_RESOURCE, {
    client: this._client,
  });

  private _runChecksMutation = new ApolloMutationController(this, RUN_QUALITY_CHECKS, {
    client: this._client,
  });

  private get _resources(): DataResource[] {
    return (this._resourcesQuery.data?.dataResources as DataResource[]) || [];
  }

  private get _loading(): boolean {
    return this._resourcesQuery.loading;
  }

  constructor() {
    super();
    this.apiBase = "/api";
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

  async _expand(id: string): Promise<void> {
    if (this._expanded === id) {
      this._expanded = null;
      this._detail = null;
      return;
    }
    this._expanded = id;
    const result = await this._client.query({
      query: GET_DATA_RESOURCE_DETAIL,
      variables: { id },
      fetchPolicy: "network-only",
    });
    this._detail = (result.data?.dataResource as DataResource) || null;
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
    await this._updateMutation.mutate({
      variables: {
        id: this._expanded,
        ann: {
          userNotes: this._editNotes,
          tags: this._editTags,
          freshnessSlaMinutes: this._editSla ? parseInt(this._editSla) : null,
          expectedRowCountMin: this._editRowMin ? parseInt(this._editRowMin) : null,
          expectedRowCountMax: this._editRowMax ? parseInt(this._editRowMax) : null,
        },
      },
    });
    this._message = { type: "success", text: "Saved" };
    this._resourcesQuery.refetch();
    await this._expand(this._expanded);
  }

  async _runChecks(): Promise<void> {
    if (!this._expanded) return;
    await this._runChecksMutation.mutate({
      variables: { id: this._expanded },
    });
    this._message = { type: "success", text: "Quality checks complete" };
    await this._expand(this._expanded);
  }

  _navigateToPlugin(name: string, kind: string): void {
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
              label: "Plugin",
              render: (r: DataResource) =>
                html`<a
                  @click=${() =>
                    this._navigateToPlugin(r.plugin.name, r.schemaName === "datasets" ? "dataset" : "source")}
                  style="cursor:pointer;text-decoration:underline;color:inherit"
                  >${r.plugin.displayName || r.plugin.name}</a
                >`,
            },
            {
              label: "Name",
              render: (r: DataResource) =>
                html`<a
                    @click=${() => this._expand(r.id)}
                    style="cursor:pointer;text-decoration:underline;color:inherit"
                    >${r.displayName}</a
                  >
                  <shenas-badge>${r.kind || "table"}</shenas-badge>`,
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
        <h3>${r.displayName} <shenas-badge>${r.kind || "table"}</shenas-badge> <span class="muted">${r.id}</span></h3>
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

        ${r.upstreamTransforms?.length || r.downstreamTransforms?.length
          ? html`
              <div class="section-label">Lineage</div>
              <div class="lineage-list">
                ${r.upstreamTransforms?.length
                  ? html`<strong>Upstream:</strong>
                      ${r.upstreamTransforms.map(
                        (u) =>
                          html` <a @click=${() => this._expand(String(u.id))}>${u.source?.displayName || u.id}</a>`,
                      )} `
                  : nothing}
                ${r.downstreamTransforms?.length
                  ? html`<strong>Downstream:</strong>
                      ${r.downstreamTransforms.map(
                        (d) =>
                          html` <a @click=${() => this._expand(String(d.id))}>${d.target?.displayName || d.id}</a>`,
                      )} `
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
