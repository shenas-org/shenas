import { LitElement, html, css } from "lit";
import { arrowQuery, buttonStyles, utilityStyles } from "shenas-frontends";

interface LogRow {
  timestamp: unknown;
  trace_id: string;
  span_id: string;
  severity: string;
  body: string;
  attributes: string | Record<string, unknown>;
  service_name: string;
}

interface SpanRow {
  trace_id: string;
  span_id: string;
  parent_span_id: string;
  name: string;
  kind: string;
  service_name: string;
  status_code: string;
  start_time: unknown;
  end_time: unknown;
  duration_ms: number | null;
  attributes: string | Record<string, unknown>;
}

class LogsPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    pipe: { type: String },
    _activeTab: { state: true },
    _logs: { state: true },
    _spans: { state: true },
    _loading: { state: true },
    _search: { state: true },
    _severity: { state: true },
    _expanded: { state: true },
    _live: { state: true },
  };

  static styles = [
    buttonStyles,
    utilityStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
      }
      .toolbar {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        padding-bottom: 0.8rem;
        flex-shrink: 0;
      }
      .tabs {
        display: flex;
        gap: 0;
        border-bottom: 2px solid var(--shenas-border, #e0e0e0);
        margin-bottom: 0.8rem;
        flex-shrink: 0;
      }
      .tab {
        padding: 0.4rem 1rem;
        cursor: pointer;
        font-size: 0.85rem;
        color: var(--shenas-text-secondary, #666);
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        background: none;
        border-top: none;
        border-left: none;
        border-right: none;
      }
      .tab.active {
        color: var(--shenas-text, #222);
        border-bottom-color: var(--shenas-primary, #0066cc);
        font-weight: 500;
      }
      .search {
        flex: 1;
        padding: 0.3rem 0.6rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      select {
        padding: 0.3rem 0.5rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        font-size: 0.85rem;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      .list {
        flex: 1;
        overflow-y: auto;
        min-height: 0;
      }
      .row {
        padding: 0.4rem 0;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        font-size: 0.8rem;
        cursor: pointer;
      }
      .row:hover {
        background: var(--shenas-bg-hover, #f5f5f5);
      }
      .row-header {
        display: flex;
        gap: 0.5rem;
        align-items: baseline;
      }
      .timestamp {
        color: var(--shenas-text-muted, #888);
        font-family: monospace;
        font-size: 0.75rem;
        min-width: 140px;
      }
      .severity {
        font-size: 0.7rem;
        font-weight: 600;
        padding: 1px 4px;
        border-radius: 3px;
        min-width: 40px;
        text-align: center;
      }
      .severity.INFO { color: var(--shenas-primary, #0066cc); background: var(--shenas-bg-selected, #f0f4ff); }
      .severity.WARNING { color: #f57c00; background: #fff3e0; }
      .severity.ERROR { color: var(--shenas-error, #c62828); background: var(--shenas-error-bg, #fce4ec); }
      .severity.DEBUG { color: var(--shenas-text-muted, #888); background: var(--shenas-bg-secondary, #fafafa); }
      .body {
        color: var(--shenas-text, #222);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .span-name {
        color: var(--shenas-text, #222);
        font-weight: 500;
        flex: 1;
      }
      .duration {
        color: var(--shenas-text-muted, #888);
        font-family: monospace;
        font-size: 0.75rem;
      }
      .status {
        font-size: 0.7rem;
        padding: 1px 4px;
        border-radius: 3px;
      }
      .status.OK { color: var(--shenas-success, #2e7d32); background: var(--shenas-success-bg, #e8f5e9); }
      .status.ERROR { color: var(--shenas-error, #c62828); background: var(--shenas-error-bg, #fce4ec); }
      .detail {
        padding: 0.5rem 0 0.5rem 1rem;
        font-size: 0.75rem;
        color: var(--shenas-text-secondary, #666);
      }
      .detail-row {
        display: flex;
        gap: 0.5rem;
        padding: 0.15rem 0;
      }
      .detail-key {
        color: var(--shenas-text-muted, #888);
        min-width: 100px;
      }
      .detail-value {
        font-family: monospace;
        word-break: break-all;
      }
      .attr-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .attr-item {
        display: flex;
        gap: 0.5rem;
      }
      .attr-key {
        color: var(--shenas-primary, #0066cc);
        min-width: 160px;
        flex-shrink: 0;
      }
      .attr-val {
        font-family: monospace;
        word-break: break-all;
        white-space: pre-wrap;
      }
      .count {
        color: var(--shenas-text-faint, #aaa);
        font-size: 0.8rem;
      }
      .live-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--shenas-success, #2e7d32);
        margin-right: 4px;
        animation: pulse 2s infinite;
      }
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
      }
      .live-label {
        font-size: 0.7rem;
        color: var(--shenas-success, #2e7d32);
      }
    `,
  ];

  declare apiBase: string;
  declare pipe: string;
  declare _activeTab: string;
  declare _logs: LogRow[];
  declare _spans: SpanRow[];
  declare _loading: boolean;
  declare _search: string;
  declare _severity: string;
  declare _expanded: number | null;
  declare _live: boolean;
  private _logSource: EventSource | null = null;
  private _spanSource: EventSource | null = null;
  private _searchTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    super();
    this.apiBase = "/api";
    this.pipe = "";
    this._activeTab = "logs";
    this._logs = [];
    this._spans = [];
    this._loading = true;
    this._search = "";
    this._severity = "";
    this._expanded = null;
    this._live = false;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.dispatchEvent(new CustomEvent("page-title", { bubbles: true, composed: true, detail: { title: "Logs" } }));
    this._fetchBoth();
    this._connectStreams();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._disconnectStreams();
    clearTimeout(this._searchTimer);
  }

  _connectStreams(): void {
    const base = this.apiBase.startsWith("http") ? this.apiBase : `${location.origin}${this.apiBase}`;
    this._logSource = new EventSource(`${base}/stream/logs`);
    this._logSource.onmessage = (e: MessageEvent) => {
      try {
        const row = JSON.parse(e.data) as LogRow;
        this._logs = [row, ...this._logs].slice(0, 500);
      } catch { /* */ }
    };
    this._logSource.onopen = () => { this._live = true; };
    this._logSource.onerror = () => { this._live = false; };

    this._spanSource = new EventSource(`${base}/stream/spans`);
    this._spanSource.onmessage = (e: MessageEvent) => {
      try {
        const row = JSON.parse(e.data) as SpanRow;
        this._spans = [row, ...this._spans].slice(0, 500);
      } catch { /* */ }
    };
  }

  _disconnectStreams(): void {
    if (this._logSource) { this._logSource.close(); this._logSource = null; }
    if (this._spanSource) { this._spanSource.close(); this._spanSource = null; }
    this._live = false;
  }

  _logsSql(extra = ""): string {
    const conds: string[] = [];
    if (this._severity) conds.push(`severity = '${this._severity}'`);
    if (this._search) conds.push(`body LIKE '%${this._search}%'`);
    if (this.pipe) conds.push(`(body LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`);
    if (extra) conds.push(extra);
    const where = conds.length ? ` WHERE ${conds.join(" AND ")}` : "";
    return `SELECT timestamp, trace_id, span_id, severity, body, attributes, service_name FROM telemetry.logs${where} ORDER BY timestamp DESC LIMIT 100`;
  }

  _spansSql(): string {
    const conds: string[] = [];
    if (this._search) conds.push(`name LIKE '%${this._search}%'`);
    if (this.pipe) conds.push(`(name LIKE '%${this.pipe}%' OR attributes LIKE '%${this.pipe}%')`);
    const where = conds.length ? ` WHERE ${conds.join(" AND ")}` : "";
    return `SELECT trace_id, span_id, parent_span_id, name, kind, service_name, status_code, start_time, end_time, duration_ms, attributes FROM telemetry.spans${where} ORDER BY start_time DESC LIMIT 100`;
  }

  async _fetchBoth(): Promise<void> {
    this._loading = true;
    try {
      const [logs, spans] = await Promise.all([
        arrowQuery(this.apiBase, this._logsSql()),
        arrowQuery(this.apiBase, this._spansSql()),
      ]);
      if (logs) this._logs = logs as LogRow[];
      if (spans) this._spans = spans as SpanRow[];
    } catch { /* */ }
    this._loading = false;
  }

  async _fetch(): Promise<void> {
    this._loading = true;
    this._expanded = null;
    try {
      if (this._activeTab === "logs") {
        this._logs = (await arrowQuery(this.apiBase, this._logsSql()) as LogRow[]) || [];
      } else {
        this._spans = (await arrowQuery(this.apiBase, this._spansSql()) as SpanRow[]) || [];
      }
    } catch { /* */ }
    this._loading = false;
  }

  _onSearch(e: InputEvent): void {
    this._search = (e.target as HTMLInputElement).value;
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => this._fetch(), 300);
  }

  _switchTab(tab: string): void {
    this._activeTab = tab;
    this._expanded = null;
    this._fetch();
  }

  _toggleExpand(idx: number): void {
    this._expanded = this._expanded === idx ? null : idx;
  }

  render() {
    const items = this._activeTab === "logs" ? this._logs : this._spans;
    return html`
      <div class="tabs">
        <button class="tab ${this._activeTab === "logs" ? "active" : ""}" @click=${() => this._switchTab("logs")}>
          Logs
        </button>
        <button class="tab ${this._activeTab === "spans" ? "active" : ""}" @click=${() => this._switchTab("spans")}>
          Spans
        </button>
      </div>
      <div class="toolbar">
        <input class="search" type="text" placeholder="Search..." .value=${this._search} @input=${this._onSearch} />
        ${this._activeTab === "logs"
          ? html`<select .value=${this._severity} @change=${(e: Event) => { this._severity = (e.target as HTMLSelectElement).value; this._fetch(); }}>
              <option value="">All severities</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>`
          : ""}
        <button @click=${() => this._fetch()}>Refresh</button>
        ${this._live ? html`<span class="live-label"><span class="live-dot"></span>Live</span>` : ""}
      </div>
      <div class="list">
        ${this._loading
          ? html`<p class="loading">Loading...</p>`
          : items.length === 0
            ? html`<p class="empty">No ${this._activeTab} found</p>`
            : items.map((item, i) => this._activeTab === "logs" ? this._renderLog(item as LogRow, i) : this._renderSpan(item as SpanRow, i))}
      </div>
    `;
  }

  _renderLog(log: LogRow, idx: number) {
    const expanded = this._expanded === idx;
    return html`
      <div class="row" @click=${() => this._toggleExpand(idx)}>
        <div class="row-header">
          <span class="timestamp">${this._formatTime(log.timestamp)}</span>
          <span class="severity ${log.severity || ""}">${log.severity || "-"}</span>
          <span class="body">${log.body || ""}</span>
        </div>
        ${expanded ? html`
          <div class="detail">
            <div style="white-space:pre-wrap; word-break:break-word; margin-bottom:0.5rem">${log.body || ""}</div>
            ${this._detailRow("Service", log.service_name)}
            ${this._detailRow("Trace ID", log.trace_id)}
            ${this._detailRow("Span ID", log.span_id)}
            ${this._renderAttributes(log.attributes)}
          </div>
        ` : ""}
      </div>
    `;
  }

  _renderSpan(span: SpanRow, idx: number) {
    const expanded = this._expanded === idx;
    return html`
      <div class="row" @click=${() => this._toggleExpand(idx)}>
        <div class="row-header">
          <span class="timestamp">${this._formatTime(span.start_time)}</span>
          <span class="status ${span.status_code || ""}">${span.status_code || "-"}</span>
          <span class="span-name">${span.name}</span>
          <span class="duration">${span.duration_ms != null ? `${Math.round(span.duration_ms)}ms` : ""}</span>
        </div>
        ${expanded ? html`
          <div class="detail">
            ${this._detailRow("Service", span.service_name)}
            ${this._detailRow("Kind", span.kind)}
            ${this._detailRow("Trace ID", span.trace_id)}
            ${this._detailRow("Span ID", span.span_id)}
            ${this._detailRow("Parent", span.parent_span_id)}
            ${this._detailRow("Status", span.status_code)}
            ${span.duration_ms != null ? this._detailRow("Duration", `${span.duration_ms.toFixed(2)}ms`) : ""}
            ${this._renderAttributes(span.attributes)}
          </div>
        ` : ""}
      </div>
    `;
  }

  _detailRow(key: string, value: string) {
    if (!value) return "";
    return html`<div class="detail-row"><span class="detail-key">${key}</span><span class="detail-value">${value}</span></div>`;
  }

  _renderAttributes(attrs: string | Record<string, unknown> | null) {
    if (!attrs) return "";
    let parsed: Record<string, unknown> = attrs as Record<string, unknown>;
    if (typeof attrs === "string") {
      try { parsed = JSON.parse(attrs); } catch { return this._detailRow("Attributes", attrs); }
    }
    if (typeof parsed !== "object" || parsed === null) return this._detailRow("Attributes", String(attrs));
    const entries = Object.entries(parsed);
    if (entries.length === 0) return "";
    return html`
      <div class="detail-row">
        <span class="detail-key">Attributes</span>
        <div class="attr-list">
          ${entries.map(([k, v]) => html`
            <div class="attr-item">
              <span class="attr-key">${k}</span>
              <span class="attr-val">${typeof v === "string" ? v : JSON.stringify(v)}</span>
            </div>
          `)}
        </div>
      </div>
    `;
  }

  _formatTime(ts: unknown): string {
    if (!ts) return "-";
    // Arrow returns DuckDB TIMESTAMP as milliseconds (possibly with sub-ms fraction)
    const d = typeof ts === "number" ? new Date(ts) : new Date(String(ts).endsWith("Z") ? ts as string : ts + "Z");
    if (isNaN(d.getTime())) return String(ts);
    const pad = (n: number, len = 2): string => String(n).padStart(len, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
}

customElements.define("shenas-logs", LogsPage);
