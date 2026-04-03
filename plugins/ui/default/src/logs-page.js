import { LitElement, html, css } from "lit";
import { buttonStyles, utilityStyles } from "./shared-styles.js";

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

  constructor() {
    super();
    this.apiBase = "/api";
    this._activeTab = "logs";
    this._logs = [];
    this._spans = [];
    this._loading = true;
    this._search = "";
    this._severity = "";
    this._expanded = null;
    this._live = false;
    this._logSource = null;
    this._spanSource = null;
  }

  connectedCallback() {
    super.connectedCallback();
    this.dispatchEvent(new CustomEvent("page-title", { bubbles: true, composed: true, detail: { title: "Logs" } }));
    this._fetchBoth();
    this._connectStreams();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._disconnectStreams();
    clearTimeout(this._searchTimer);
  }

  _connectStreams() {
    const base = this.apiBase.startsWith("http") ? this.apiBase : `${location.origin}${this.apiBase}`;
    this._logSource = new EventSource(`${base}/stream/logs`);
    this._logSource.onmessage = (e) => {
      try {
        const row = JSON.parse(e.data);
        this._logs = [row, ...this._logs].slice(0, 500);
      } catch { /* */ }
    };
    this._logSource.onopen = () => { this._live = true; };
    this._logSource.onerror = () => { this._live = false; };

    this._spanSource = new EventSource(`${base}/stream/spans`);
    this._spanSource.onmessage = (e) => {
      try {
        const row = JSON.parse(e.data);
        this._spans = [row, ...this._spans].slice(0, 500);
      } catch { /* */ }
    };
  }

  _disconnectStreams() {
    if (this._logSource) { this._logSource.close(); this._logSource = null; }
    if (this._spanSource) { this._spanSource.close(); this._spanSource = null; }
    this._live = false;
  }

  async _fetchBoth() {
    this._loading = true;
    const pipeQs = this.pipe ? `?pipe=${encodeURIComponent(this.pipe)}` : "";
    try {
      const [logsResp, spansResp] = await Promise.all([
        fetch(`${this.apiBase}/logs${pipeQs}`),
        fetch(`${this.apiBase}/spans${pipeQs}`),
      ]);
      if (logsResp.ok) this._logs = await logsResp.json();
      if (spansResp.ok) this._spans = await spansResp.json();
    } catch { /* */ }
    this._loading = false;
  }

  async _fetch() {
    this._loading = true;
    this._expanded = null;
    const params = new URLSearchParams();
    if (this._search) params.set("search", this._search);
    if (this._activeTab === "logs" && this._severity) params.set("severity", this._severity);
    if (this.pipe) params.set("pipe", this.pipe);
    const qs = params.toString() ? `?${params}` : "";
    try {
      const endpoint = this._activeTab === "logs" ? "logs" : "spans";
      const resp = await fetch(`${this.apiBase}/${endpoint}${qs}`);
      if (resp.ok) {
        const data = await resp.json();
        if (this._activeTab === "logs") this._logs = data;
        else this._spans = data;
      }
    } catch { /* */ }
    this._loading = false;
  }

  _onSearch(e) {
    this._search = e.target.value;
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(() => this._fetch(), 300);
  }

  _switchTab(tab) {
    this._activeTab = tab;
    this._expanded = null;
    this._fetch();
  }

  _toggleExpand(idx) {
    this._expanded = this._expanded === idx ? null : idx;
  }

  render() {
    const items = this._activeTab === "logs" ? this._logs : this._spans;
    return html`
      <div class="tabs">
        <button class="tab ${this._activeTab === "logs" ? "active" : ""}" @click=${() => this._switchTab("logs")}>
          Logs <span class="count">(${this._logs.length})</span>
        </button>
        <button class="tab ${this._activeTab === "spans" ? "active" : ""}" @click=${() => this._switchTab("spans")}>
          Spans <span class="count">(${this._spans.length})</span>
        </button>
      </div>
      <div class="toolbar">
        <input class="search" type="text" placeholder="Search..." .value=${this._search} @input=${this._onSearch} />
        ${this._activeTab === "logs"
          ? html`<select .value=${this._severity} @change=${(e) => { this._severity = e.target.value; this._fetch(); }}>
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
            : items.map((item, i) => this._activeTab === "logs" ? this._renderLog(item, i) : this._renderSpan(item, i))}
      </div>
    `;
  }

  _renderLog(log, idx) {
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
            ${this._detailRow("Service", log.service_name)}
            ${this._detailRow("Trace ID", log.trace_id)}
            ${this._detailRow("Span ID", log.span_id)}
            ${this._renderAttributes(log.attributes)}
          </div>
        ` : ""}
      </div>
    `;
  }

  _renderSpan(span, idx) {
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

  _detailRow(key, value) {
    if (!value) return "";
    return html`<div class="detail-row"><span class="detail-key">${key}</span><span class="detail-value">${value}</span></div>`;
  }

  _renderAttributes(attrs) {
    if (!attrs) return "";
    let parsed = attrs;
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

  _formatTime(ts) {
    if (!ts) return "-";
    return String(ts).replace("T", " ").slice(0, 23);
  }
}

customElements.define("shenas-logs", LogsPage);
