/**
 * Hypotheses tab (PR 3.2): user types a question, the LLM emits a recipe,
 * the runner executes it, the user sees the result + plan + recipe and can
 * promote it to a canonical metric. Iterate / branch is deferred to PR 4.7.
 */
import { LitElement, html, css } from "lit";
import { gql, gqlFull, buttonStyles, messageStyles, utilityStyles } from "shenas-frontends";

interface HypothesisRow {
  id: number;
  question: string;
  plan: string;
  inputs: string[];
  interpretation: string;
  model: string;
  promoted_to: string | null;
  created_at: string | null;
  recipe: unknown;
  result: unknown;
}

class HypothesesPage extends LitElement {
  static properties = {
    apiBase: { type: String, attribute: "api-base" },
    _hypotheses: { state: true },
    _selectedId: { state: true },
    _question: { state: true },
    _busy: { state: true },
    _error: { state: true },
    _promoteName: { state: true },
  };

  declare apiBase: string;
  declare _hypotheses: HypothesisRow[];
  declare _selectedId: number | null;
  declare _question: string;
  declare _busy: boolean;
  declare _error: string;
  declare _promoteName: string;

  static styles = [
    buttonStyles,
    messageStyles,
    utilityStyles,
    css`
      :host {
        display: flex;
        gap: 1rem;
        height: 100%;
      }
      .sidebar {
        width: 280px;
        border-right: 1px solid var(--shenas-border, #e0e0e0);
        padding-right: 1rem;
        overflow-y: auto;
      }
      .main {
        flex: 1;
        overflow-y: auto;
      }
      .ask {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
      }
      .ask textarea {
        flex: 1;
        min-height: 60px;
        padding: 0.5rem;
        font-family: inherit;
        font-size: 0.9rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
        background: var(--shenas-bg, #fff);
        color: var(--shenas-text, #222);
      }
      .row {
        padding: 0.5rem;
        border-bottom: 1px solid var(--shenas-border-light, #f0f0f0);
        cursor: pointer;
      }
      .row:hover {
        background: var(--shenas-bg-secondary, #fafafa);
      }
      .row.selected {
        background: var(--shenas-bg-accent, #eef);
      }
      .question {
        font-weight: 500;
        font-size: 0.85rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .meta {
        font-size: 0.7rem;
        color: var(--shenas-text-muted, #888);
      }
      .promoted {
        color: var(--shenas-accent, #2a8);
      }
      .panel {
        background: var(--shenas-bg-secondary, #fafafa);
        border: 1px solid var(--shenas-border-light, #f0f0f0);
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
      }
      .panel h3 {
        margin: 0 0 0.5rem 0;
        font-size: 0.85rem;
        color: var(--shenas-text-muted, #888);
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .panel pre {
        margin: 0;
        font-size: 0.75rem;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .scalar {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--shenas-text, #222);
      }
      .error {
        color: var(--shenas-error, #c33);
      }
      .promote-bar {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        margin-top: 1rem;
      }
      .promote-bar input {
        padding: 0.3rem 0.6rem;
        font-size: 0.85rem;
        border: 1px solid var(--shenas-border-input, #ddd);
        border-radius: 4px;
      }
    `,
  ];

  constructor() {
    super();
    this.apiBase = "";
    this._hypotheses = [];
    this._selectedId = null;
    this._question = "";
    this._busy = false;
    this._error = "";
    this._promoteName = "";
  }

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  async _load(): Promise<void> {
    const data = await gql(this.apiBase, `{ hypotheses }`);
    this._hypotheses = (data?.hypotheses as HypothesisRow[]) || [];
    if (this._hypotheses.length > 0 && this._selectedId === null) {
      this._selectedId = this._hypotheses[0].id;
    }
  }

  async _ask(): Promise<void> {
    const q = this._question.trim();
    if (!q) return;
    this._busy = true;
    this._error = "";
    try {
      const data = await gqlFull(this.apiBase, `mutation($q: String!) { askHypothesis(question: $q) }`, { q });
      const body = (data?.data?.["askHypothesis"] ?? {}) as { id?: number; error?: { message?: string } };
      if (body?.error) {
        this._error = body.error.message || "LLM call failed";
      } else if (body?.id) {
        this._selectedId = body.id;
      }
      this._question = "";
      await this._load();
    } catch (exc) {
      this._error = String(exc);
    } finally {
      this._busy = false;
    }
  }

  async _promote(): Promise<void> {
    if (!this._selectedId || !this._promoteName) return;
    const data = await gqlFull(
      this.apiBase,
      `mutation($id: Int!, $name: String!) { promoteHypothesis(hypothesisId: $id, name: $name) }`,
      { id: this._selectedId, name: this._promoteName },
    );
    const body = (data?.data?.["promoteHypothesis"] ?? {}) as { error?: string };
    if (body?.error) {
      this._error = body.error;
    } else {
      this._promoteName = "";
      await this._load();
    }
  }

  _select(id: number): void {
    this._selectedId = id;
    this._error = "";
  }

  _renderResult(result: unknown): unknown {
    if (!result || typeof result !== "object") return html`<p class="meta">No result yet.</p>`;
    const r = result as { type?: string; value?: unknown; rows?: unknown[]; columns?: string[]; message?: string };
    if (r.type === "scalar") {
      return html`<div class="scalar">${String(r.value ?? "—")}</div>`;
    }
    if (r.type === "table") {
      const rows = r.rows || [];
      const cols = r.columns || [];
      return html`
        <table>
          <thead>
            <tr>
              ${cols.map((c) => html`<th>${c}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${rows.slice(0, 50).map(
              (row) => html`
                <tr>
                  ${cols.map((c) => html`<td>${String((row as Record<string, unknown>)[c] ?? "")}</td>`)}
                </tr>
              `,
            )}
          </tbody>
        </table>
        ${rows.length > 50 ? html`<p class="meta">Showing 50 of ${rows.length} rows.</p>` : ""}
      `;
    }
    if (r.type === "error") {
      return html`<p class="error">${r.message}</p>`;
    }
    return html`<pre>${JSON.stringify(r, null, 2)}</pre>`;
  }

  _renderSelected(): unknown {
    const h = this._hypotheses.find((x) => x.id === this._selectedId);
    if (!h) return html`<p class="meta">No hypothesis selected.</p>`;
    return html`
      <h2>${h.question}</h2>
      <p class="meta">
        ${h.created_at || ""} · ${h.model || "—"}
        ${h.promoted_to ? html` · <span class="promoted">→ ${h.promoted_to}</span>` : ""}
      </p>

      ${h.plan
        ? html`<div class="panel">
            <h3>Plan</h3>
            <p>${h.plan}</p>
          </div>`
        : ""}

      <div class="panel">
        <h3>Recipe</h3>
        <pre>${JSON.stringify(h.recipe, null, 2)}</pre>
      </div>

      <div class="panel">
        <h3>Result</h3>
        ${this._renderResult(h.result)}
      </div>

      ${h.interpretation
        ? html`<div class="panel">
            <h3>Interpretation</h3>
            <p>${h.interpretation}</p>
          </div>`
        : ""}
      ${!h.promoted_to
        ? html`
            <div class="promote-bar">
              <input
                type="text"
                placeholder="metric_name (snake_case)"
                .value=${this._promoteName}
                @input=${(e: InputEvent) => {
                  this._promoteName = (e.target as HTMLInputElement).value;
                }}
              />
              <button @click=${this._promote} ?disabled=${!this._promoteName}>Promote</button>
            </div>
          `
        : ""}
    `;
  }

  render() {
    return html`
      <div class="sidebar">
        ${this._hypotheses.length === 0
          ? html`<p class="meta">No hypotheses yet. Ask a question to get started.</p>`
          : this._hypotheses.map(
              (h) => html`
                <div class="row ${h.id === this._selectedId ? "selected" : ""}" @click=${() => this._select(h.id)}>
                  <div class="question">${h.question}</div>
                  <div class="meta">
                    #${h.id} ${h.promoted_to ? html`<span class="promoted">· promoted</span>` : ""}
                  </div>
                </div>
              `,
            )}
      </div>
      <div class="main">
        <div class="ask">
          <textarea
            placeholder="Ask a question about your data..."
            .value=${this._question}
            @input=${(e: InputEvent) => {
              this._question = (e.target as HTMLTextAreaElement).value;
            }}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                this._ask();
              }
            }}
          ></textarea>
          <button @click=${this._ask} ?disabled=${this._busy || !this._question.trim()}>
            ${this._busy ? "Asking..." : "Ask"}
          </button>
        </div>
        ${this._error ? html`<p class="error">${this._error}</p>` : ""} ${this._renderSelected()}
      </div>
    `;
  }
}

customElements.define("shenas-hypotheses", HypothesesPage);
