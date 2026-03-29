import { LitElement, html, css } from "lit";

class ShenasApp extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _pipes: { state: true },
    _dbStatus: { state: true },
    _components: { state: true },
    _loading: { state: true },
  };

  static styles = css`
    :host {
      display: block;
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1rem;
      color: #222;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 1.5rem;
    }
    .header img {
      width: 48px;
      height: 48px;
    }
    .header h1 {
      margin: 0;
      font-size: 1.5rem;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .card {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1rem;
      background: #fff;
    }
    .card h3 {
      margin: 0 0 0.5rem;
      font-size: 1rem;
    }
    .card .meta {
      color: #888;
      font-size: 0.85rem;
    }
    .card .commands {
      margin-top: 0.5rem;
      font-size: 0.85rem;
      color: #555;
    }
    .section {
      margin: 2rem 0;
    }
    .section h2 {
      font-size: 1.1rem;
      border-bottom: 1px solid #e0e0e0;
      padding-bottom: 0.5rem;
    }
    .status {
      font-size: 0.9rem;
      color: #555;
    }
    .status code {
      background: #f0f0f0;
      padding: 2px 6px;
      border-radius: 3px;
    }
    a {
      color: #0066cc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .loading {
      color: #888;
      font-style: italic;
    }
  `;

  constructor() {
    super();
    this.apiBase = "/api";
    this._pipes = [];
    this._dbStatus = null;
    this._components = [];
    this._loading = true;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
  }

  async _fetchData() {
    this._loading = true;
    try {
      const [pipes, db, components] = await Promise.all([
        this._fetch("/plugins/pipe"),
        this._fetch("/db/status"),
        this._fetch("/plugins/component"),
      ]);
      this._pipes = pipes || [];
      this._dbStatus = db;
      this._components = components || [];
    } catch (e) {
      console.error("Failed to fetch data:", e);
    }
    this._loading = false;
  }

  async _fetch(path) {
    const resp = await fetch(`${this.apiBase}${path}`);
    if (!resp.ok) return null;
    return resp.json();
  }

  render() {
    if (this._loading) {
      return html`<p class="loading">Loading...</p>`;
    }

    return html`
      <div class="header">
        <img src="/static/images/shenas.png" alt="shenas" />
        <h1>shenas</h1>
      </div>

      ${this._renderDb()} ${this._renderPipes()} ${this._renderComponents()}
    `;
  }

  _renderDb() {
    const db = this._dbStatus;
    if (!db) return html``;
    return html`
      <div class="section">
        <h2>Database</h2>
        <div class="status">
          <p>Path: <code>${db.db_path}</code></p>
          ${db.size_mb != null
            ? html`<p>Size: ${db.size_mb} MB</p>`
            : html`<p>Not created yet</p>`}
          ${(db.schemas || []).map(
            (s) => html`
              <p>
                <strong>${s.name}</strong>: ${s.tables.length} tables,
                ${s.tables.reduce((sum, t) => sum + t.rows, 0)} rows
              </p>
            `,
          )}
        </div>
      </div>
    `;
  }

  _renderPipes() {
    return html`
      <div class="section">
        <h2>Pipes</h2>
        ${this._pipes.length === 0
          ? html`<p class="status">No pipes installed</p>`
          : html`
              <div class="cards">
                ${this._pipes.map(
                  (p) => html`
                    <div class="card">
                      <h3>${p.name}</h3>
                      <div class="meta">${p.version}</div>
                      <div class="commands">
                        ${(p.commands || []).join(", ")}
                      </div>
                    </div>
                  `,
                )}
              </div>
            `}
      </div>
    `;
  }

  _renderComponents() {
    return html`
      <div class="section">
        <h2>Components</h2>
        ${this._components.length === 0
          ? html`<p class="status">No components installed</p>`
          : html`
              <div class="cards">
                ${this._components.map(
                  (c) => html`
                    <div class="card">
                      <h3>
                        <a href="/components/${c.name}/${c.html || "index.html"}">${c.name}</a>
                      </h3>
                      <div class="meta">${c.version}</div>
                      ${c.description
                        ? html`<div class="commands">${c.description}</div>`
                        : ""}
                    </div>
                  `,
                )}
              </div>
            `}
      </div>
    `;
  }
}

customElements.define("shenas-app", ShenasApp);
