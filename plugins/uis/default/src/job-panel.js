import { LitElement, html, css } from "lit";

class JobPanel extends LitElement {
  static properties = {
    _jobs: { state: true },
    _collapsed: { state: true },
  };

  static styles = css`
    :host {
      display: block;
    }
    :host([hidden]) {
      display: none;
    }
    .panel {
      border-top: 1px solid var(--shenas-border, #e0e0e0);
      background: var(--shenas-bg, #fff);
      display: flex;
      flex-direction: column;
      max-height: 200px;
    }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.3rem 0.8rem;
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--shenas-text-secondary, #666);
      cursor: pointer;
      user-select: none;
      flex-shrink: 0;
    }
    .header:hover {
      background: var(--shenas-bg-hover, #f5f5f5);
    }
    .badge {
      background: var(--shenas-accent, #728F67);
      color: #fff;
      border-radius: 8px;
      padding: 0 0.4rem;
      font-size: 0.65rem;
      margin-left: 0.4rem;
    }
    .chevron {
      transition: transform 0.15s;
      font-size: 0.7rem;
    }
    .chevron.up {
      transform: rotate(180deg);
    }
    .log-area {
      overflow-y: auto;
      flex: 1;
      padding: 0 0.8rem 0.4rem;
      font-family: monospace;
      font-size: 0.75rem;
      line-height: 1.5;
      color: var(--shenas-text, #222);
    }
    .job-group {
      margin-bottom: 0.4rem;
    }
    .job-label {
      font-weight: 600;
      color: var(--shenas-text-secondary, #666);
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.15rem 0;
    }
    .job-label .status {
      font-size: 0.7rem;
    }
    .spinning {
      display: inline-block;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .line {
      color: var(--shenas-text-muted, #999);
      padding-left: 1rem;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .line.error {
      color: var(--shenas-error, #c62828);
    }
    .line.success {
      color: var(--shenas-success, #2e7d32);
    }
    .dismiss {
      background: none;
      border: none;
      color: var(--shenas-text-muted, #999);
      cursor: pointer;
      font-size: 0.7rem;
      padding: 0.1rem 0.3rem;
    }
    .dismiss:hover {
      color: var(--shenas-text, #222);
    }
  `;

  constructor() {
    super();
    this._jobs = [];
    this._collapsed = false;
  }

  get _hasJobs() {
    return this._jobs.length > 0;
  }

  get _activeCount() {
    return this._jobs.filter((j) => j.status === "running").length;
  }

  addJob(id, label) {
    this._jobs = [...this._jobs, { id, label, status: "running", lines: [] }];
    this._collapsed = false;
    this._scrollToBottom();
  }

  appendLine(id, text) {
    this._jobs = this._jobs.map((j) =>
      j.id === id ? { ...j, lines: [...j.lines, text] } : j,
    );
    this._scrollToBottom();
  }

  finishJob(id, ok, message) {
    this._jobs = this._jobs.map((j) =>
      j.id === id ? { ...j, status: ok ? "done" : "error", message } : j,
    );
  }

  _scrollToBottom() {
    requestAnimationFrame(() => {
      const area = this.shadowRoot?.querySelector(".log-area");
      if (area) area.scrollTop = area.scrollHeight;
    });
  }

  _dismiss(id) {
    this._jobs = this._jobs.filter((j) => j.id !== id);
  }

  _dismissAll() {
    this._jobs = this._jobs.filter((j) => j.status === "running");
  }

  render() {
    if (!this._hasJobs) return "";

    const finished = this._jobs.filter((j) => j.status !== "running").length;

    return html`
      <div class="panel">
        <div class="header" @click=${() => { this._collapsed = !this._collapsed; }}>
          <span>
            Jobs
            ${this._activeCount > 0
              ? html`<span class="badge">${this._activeCount}</span>`
              : ""}
          </span>
          <span>
            ${finished > 0
              ? html`<button class="dismiss" @click=${(e) => { e.stopPropagation(); this._dismissAll(); }}>Clear</button>`
              : ""}
            <span class="chevron ${this._collapsed ? "" : "up"}">\u25BC</span>
          </span>
        </div>
        ${this._collapsed ? "" : html`
          <div class="log-area">
            ${this._jobs.map((job) => html`
              <div class="job-group">
                <div class="job-label">
                  <span class="status">
                    ${job.status === "running"
                      ? html`<span class="spinning">\u25E0</span>`
                      : job.status === "done" ? "\u2713" : "\u2717"}
                  </span>
                  ${job.label}
                  ${job.status !== "running"
                    ? html`<button class="dismiss" @click=${() => this._dismiss(job.id)}>\u2715</button>`
                    : ""}
                </div>
                ${job.lines.map((line) => html`
                  <div class="line ${job.status === "error" ? "error" : ""}">${line}</div>
                `)}
                ${job.message ? html`
                  <div class="line ${job.status === "done" ? "success" : "error"}">${job.message}</div>
                ` : ""}
              </div>
            `)}
          </div>
        `}
      </div>
    `;
  }
}

customElements.define("shenas-job-panel", JobPanel);
